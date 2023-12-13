# This script creates the emails which are beeing send
# if a resource reaches a specific threshold
# It uses the back_end/notification_resource.csv to track
# the last email notifications sent to prevent spaming the recipients.
# Furthermore it uses the back_end/resource_overview.csv to create the attachments,
# containing the whole resource overview, sent to the recipients

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

from tempfile import NamedTemporaryFile
import shutil
# import os

import csv
import ssl
import smtplib

import datetime as dt

import back_end.email_config as email_config 


class EmailFactory():
    def __init__(self, recipients, resources, attachments_raw):
        self.recipients = recipients
        self.attachments_raw = attachments_raw
        self.resource_names = []
        self.resource_amounts = []
        for e in resources:
            self.resource_names.append(e[0])
            self.resource_amounts.append(e[1])

        self.print_rn=""
        for e in resources:
            self.print_rn = self.print_rn + "\n\t\t\t > Resource name: " + e[0] + "\t\t Resource amount: " + str(e[1])

        self.fields = ["resource_name", "last_notification"]

        self.subject = "Coffee Resource Update"
        self.body = f"""
                    Hello,

                    You receive this mail because you have registered for E-Mail notifications,
                    when a resource reaches a critical amount.
                    If you don't want to receive this mail you can easily change it
                    under your profile configuration!

                    Resources with critical amount:{self.print_rn}                

                    You can find a resource overview in the attachment.

                    If you want to consume coffee in the future,
                    please restock the critical resource, after discussing in VISUS.

                    Have a nice day :)
                    
                    Greetings
                    """


    def notification_needed(self):
        # TODO maybe in rasp pi needed
        # print(os.getcwd())
        rn = self.resource_names

        with open('back_end/notification_resource.csv', mode='r') as csv_file:
            csv_reader = csv.DictReader(csv_file, fieldnames=self.fields)
            line_count = 0
            for row in csv_reader:
                if row["resource_name"] in rn:
                    csv_date = dt.datetime.strptime(row["last_notification"],"%Y-%m-%d").date()
                    week_ago =  dt.date.today() - dt.timedelta(days=email_config.NOTIFICATION_DELTA)
                    rn.remove(row['resource_name'])
                    if csv_date < week_ago:
                        return True
                line_count += 1
            if line_count == 0 or rn:
                return True
            return False

    def update_notification_csv(self):
        tempfile = NamedTemporaryFile(mode='w', newline='',delete=False)

        with open("back_end/notification_resource.csv", 'r') as csvfile, tempfile:
            reader = csv.DictReader(csvfile, fieldnames=self.fields)
            writer = csv.DictWriter(tempfile, fieldnames=self.fields)
            rn = self.resource_names
        
            for row in reader:
                if row['resource_name'] in rn:
                    print('updating row', row['resource_name'])
                    row['last_notification']= dt.date.today()
                    rn.remove(row['resource_name'])
                else:
                    row = {'resource_name': row['resource_name'], 'last_notification': row['last_notification']}
                writer.writerow(row)
            
            if rn:
                for ele in rn:
                    row = {'resource_name': ele, 'last_notification': dt.date.today()}
                    writer.writerow(row)
        shutil.move(tempfile.name, "back_end/notification_resource.csv")
  
    def create_resource_csv(self):
        cols = ['Resource Name' ,'Amount']
        with open("back_end/resource_overview.csv", 'w', newline='') as file:
            file.truncate() # deleting all entries
            writer = csv.writer(file)
            writer.writerow(cols)
            r_type = 0
            for att in self.attachments_raw:
                if r_type == 0: # resource type is coffee
                    writer.writerow(["################## COFFEE ##################"])
                    for r in att:
                        writer.writerow([r[0], r[1]])
                elif r_type == 1: # resource type is milk
                    writer.writerow(["################## MILK ##################"])
                    for r in att:
                        writer.writerow([r[0], r[1]])
                elif r_type == 2: # resource type is sugar
                    writer.writerow(["################## SUGAR ##################"])
                    for r in att:
                        writer.writerow([r[0], r[1]])
                r_type += 1


    def send_mail(self):
        if self.notification_needed():
            self.create_resource_csv()

            em = MIMEMultipart()
            em['From'] = email_config.EMAIL_SENDER
            em['To'] = ", ".join(self.recipients[0])
            em['Subject'] = self.subject
            m_body = MIMEText(self.body)
            em.attach(m_body)

            part = MIMEBase('application', "octet-stream")
            part.set_payload(open("back_end/resource_overview.csv", "rb").read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', 'attachment', filename="resource_overview.csv")

            em.attach(part)

            context = ssl.create_default_context()

            with smtplib.SMTP_SSL(email_config.SMTP_SERVER, email_config.PORT, context=context) as smtp:
                smtp.login(email_config.EMAIL_SENDER, email_config.EMAIL_PASSWORD)
                smtp.sendmail(email_config.EMAIL_SENDER, self.recipients, em.as_string())
        
            self.update_notification_csv()

    

