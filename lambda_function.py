from bs4 import BeautifulSoup
import json
import os
import tempfile
import requests
import boto3
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import smtplib


_URL = "https://owasp.org/www-pdf-archive/"
_S3_BUCKET_NAME = "filestorexxxxxxxeshs"
sender_email = "rakeshsxxxxxx@gmail.com"
recipient_email = "rakxxxxxx@gmail.com"
aws_region = "eu-west-2"
gmail_username = "rakeshsingxxxxxx@gmail.com"
gmail_password = "xxxxxxxxxxxxxxxxxxxx"


def lambda_handler(event, context):
    download_and_upload_to_s3()
    download_from_s3_and_send_email(_S3_BUCKET_NAME)

    response = {
        "statusCode": 200,
        "body": json.dumps({"message": "Files downloaded and uploaded to S3"})
    }

    return response


def download_and_upload_to_s3():
    response = requests.get(_URL)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        links = soup.find_all('a', href=lambda href: (href and href.endswith('pdf')))

        s3_client = boto3.client('s3')
        limit = 3
        counter = 0
        print(len(links))
        for link in links:
            file_url = link['href']
            file_name = os.path.basename(file_url)

            if os.name == 'nt':
                tempdir = tempfile.gettempdir()
                file_path = os.path.join(tempdir, file_name)
            else:
                file_path = f"/tmp/{file_name}"

            # Download the file
            file_response = requests.get('https://owasp.org/'+file_url)
            with open(file_path, 'wb') as file:
                file.write(file_response.content)

            # Upload the file to S3
            s3_object_key = f"downloads/{file_name}"
            s3_client.upload_file(file_path, _S3_BUCKET_NAME, s3_object_key)

            print(f"Downloaded and uploaded to S3: {file_name}")

            # Clean up the temporary file
            os.remove(file_path)
            if counter > limit:
                break
            counter += 1


def download_from_s3_and_send_email(s3_bucket_name):
    s3_client = boto3.client('s3', region_name=aws_region)

    # List all objects in the S3 bucket
    response = s3_client.list_objects_v2(Bucket=s3_bucket_name)

    if 'Contents' in response:
        for obj in response['Contents']:
            file_key = obj['Key']

            # Create a temporary directory to store the downloaded file
            temp_dir = tempfile.mkdtemp()
            local_file_path = os.path.join(temp_dir, os.path.basename(file_key))

            # Download the file from S3
            s3_client.download_file(s3_bucket_name, file_key, local_file_path)

            # Create the email message
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = recipient_email
            msg['Subject'] = "File Attached"

            # Attach the file to the email
            with open(local_file_path, 'rb') as file:
                attachment = MIMEApplication(file.read(), Name=os.path.basename(file_key))
                attachment['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_key)}"'
                msg.attach(attachment)

            # Send the email using Gmail SMTP
            with smtplib.SMTP('smtp.gmail.com', 587) as server:
                server.starttls()
                server.login(gmail_username, gmail_password)
                server.sendmail(sender_email, recipient_email, msg.as_string())

            print(f"Email sent with attachment: {file_key}")

            # Clean up the temporary directory
            os.remove(local_file_path)
            os.rmdir(temp_dir)

            # Delete the file from S3 after sending the email
            s3_client.delete_object(Bucket=s3_bucket_name, Key=file_key)
            print(f"File deleted from S3: {file_key}")


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    lambda_handler('PyCharm', '')

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
