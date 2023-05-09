import dns.resolver
import dns.rdatatype
import smtplib
import configparser
import os

# Read configuration file
config = configparser.ConfigParser()
if not os.path.exists('config.ini'):
    raise FileNotFoundError('Config file not found')
config.read('config.ini')

# Read email accounts and selector from config file
try:
    email_accounts = config.get('emails', 'email_accounts').splitlines()
    selector = config.get('emails', 'selector')
    nameservers = config.get('resolver', 'nameservers').split(',')
    timeout = config.getfloat('resolver', 'timeout')
except configparser.Error as e:
    print(f'Error reading configuration file: {e}')
    exit()

# Set up DNS resolver with specified nameservers and timeout
resolver = dns.resolver.Resolver(configure=False)
resolver.nameservers = [ns.strip() for ns in nameservers]
resolver.timeout = timeout

# Initialize failure counter
failure_count = 0

# Loop through email accounts and check DNS records
for email in email_accounts:
    print(f'\n\nChecking email address {email}')

    # Extract domain from email
    domain = email.split('@')[-1]

    try:
        # Check MX record for domain
        mx_records = resolver.resolve(domain, 'MX')
        mx_hostnames = [mx.exchange.to_text() for mx in mx_records]
        print(f'MX records for domain {domain}: {mx_hostnames}')
    except dns.resolver.NoAnswer as e:
        print(f'Error checking MX records for domain {domain}: {e}')
        failure_count += 1

    try:
        # Check TXT record for SPF
        spf_records = resolver.resolve(domain, 'TXT')
        spf_strings = [spf.to_text()
                       for spf in spf_records if 'v=spf1' in spf.to_text()]
        if spf_strings:
            print(f'SPF record for domain {domain}: {spf_strings[0]}')
        else:
            print(f'No SPF record found for domain {domain}')
            failure_count += 1
    except dns.resolver.NoAnswer as e:
        print(f'Error checking SPF records for domain {domain}: {e}')
        failure_count += 1

    try:
        # Check TXT record for DKIM
        dkim_records = resolver.resolve(
            f'{selector}._domainkey.{domain}', 'TXT')
        dkim_strings = [dkim.to_text()
                        for dkim in dkim_records if 'v=DKIM1' in dkim.to_text()]
        if dkim_strings:
            print(f'DKIM record for email {email}: {dkim_strings[0]}')
        else:
            print(f'No DKIM record found for email {email}')
            failure_count += 1
    except dns.resolver.NoAnswer as e:
        print(f'Error checking DKIM records for email {email}: {e}')
        failure_count += 1

    # Test SMTP connection to MX hostname
    for mx_hostname in mx_hostnames:
        try:
            with smtplib.SMTP(mx_hostname) as smtp:
                smtp.helo()
                smtp.mail('test@test.com')
                smtp.rcpt(email)
                smtp.quit()
            print(f'Email address {email} is working')
            break
        except Exception as e:
            print(
                f'Error testing email address {email} with MX hostname {mx_hostname}: {e}')
            failure_count += 1

# Print summary of failures
print(f'\n\nTotal number of failures: {failure_count}')
