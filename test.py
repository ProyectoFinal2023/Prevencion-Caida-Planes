import boto3

ses_client = boto3.client('ses', region_name='us-east-2')  # Replace with your desired region

def send_email(subject, message):
    try:
        response = ses_client.send_email(
            Source="agustin.bergoglio@hotmail.com",  # Replace with your email address
            Destination={
                'ToAddresses': ["agustin.bergoglio@hotmail.com"],  # Replace with the recipient's email address
            },
            Message={
                'Subject': {'Data': subject},
                'Body': {'Text': {'Data': message}},
            }
        )
    except Exception as e:
        print("Error sending email: %s", str(e))


# Example usage:
send_email('agustin.bergoglio@hotmail.com', 'Test Subject')


