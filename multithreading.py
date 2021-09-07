from email.mime.application import MIMEApplication  # For the email client
from email.mime.multipart import MIMEMultipart      # For the email client
from beautifultable import BeautifulTable           # For the 'Beautiful table of ip addresses'
from email.mime.text import MIMEText                # Again for the email client but I sorted it so it goes from longest to shortest
from getmac import get_mac_address                  # For getting the mac address of every ip
from operator import itemgetter                     # For sorting the responses
from datetime import datetime                       # Used to get the current date and time
from threading import Thread                        # For multithreading which makes it run a 'little' faster
from string import Template                         # For the email client
import threading                                    # For locking data so the threads won't have to fight over who gets what and eventually overwrite everyone's data
import requests                                     # For making GET requests
import smtplib                                      # For connecting to a email server
import os                                           # For removing the log file after we are done





# EMail address for login
MY_ADDRESS = '################@gmail.com' # Ik wil niet toegang geven to het email address van de bot dus ik heb het vervangen met '#'

# Password for login
PASSWORD = 'UrRepeatersAreDeadSoFixThem'

# IP range
iprange = 254

# Mac addresses of the repeaters to check for
repeaterMac = {'32:91:ab:06:2a:9a', '32:91:ab:ab:06:9e', '32:91:ab:00:fc:6e'}

# Vendor
repeaterMacStart = '32:91:ab'

# Email receiver
receiver = 'mariodeu2@gmail.com'
#receiver = 'kj######@gmail.com' # Privacy redenen even vervangen met '#'

# Email subject
subject = "Repeater might be offline :("

# Timout for GET requests
timeout = 10





# Saving datetime to a variable
filename = 'log_' + datetime.now().strftime("%d.%m.%Y-%H.%M.%S") + '.txt'

responses = []                                      # Used for storing the responses in this format: (IP, MAC, Response Code)
responses_lock = threading.Lock()                   # Locking it so it becomes 'threadsafe'





def getMAC(ip):
    mac = get_mac_address(ip=ip) # Getting the mac address from the ip

    if(mac == '00:00:00:00:00:00'):
        mac = ''

    if(len(str(mac)) == 17):

        # Making a GET request in a thread lock
        with mac_lock:
            get = requests.get(
                'https://api.macvendors.com/v1/lookup/' + mac,
                timeout=timeout,
                headers={'Accept': 'text/plain', 'Authorization': 'Bearer BEARER TOKEN HIER'}
            )

        # If a known error comes it formats it in plain/text instead of json
        if(get.text.startswith('{"errors":{"detail":"Not Found"}}') == True):
            vendor = '-'

        elif(get.text.startswith('{"errors":{"detail":"Unauthorized"}}') == True):
             vendor = 'Api key invalid (Unauthorized)'

        elif(get.text.startswith('{"errors":{"detail":"Too Many Requests"') == True):
             vendor = 'Too many requests'

        else:
            vendor = get.text

    else:
        vendor = ''

    return mac, vendor

mac_lock = threading.Lock() # Used for creating a delay between the threads sending an GET request to the server

def check(i):
    # Setting up some variables using the 'i' provided
    ip = '192.168.178.' + str(i+1)

    # Make a GET request to the given IP address to find out if it's alive
    try:
        get = requests.get('http://' + ip, timeout=timeout)# Make a GET request to the IP address

        mac, vendor = getMAC(ip)

        with responses_lock: # Acquire lock
            responses.append((i+1, mac, get.status_code, vendor))# Saving the response

    # If it gives an error (Maybe because the IP isn't hosting a webserver) save the information (Only if the mac is longer than 17 characters)
    except Exception as e:
        mac, vendor = getMAC(ip)
        if(len(str(mac)) >= 17):
            with responses_lock: # Acquire lock
                responses.append((i+1, mac, '-', vendor)) # Saving the response





threads = []

def startThread(i):
    thread = Thread(target=check, args={i})
    thread.start()
    threads.append(thread)

for i in range(iprange):
    while(True):
        try:
            startThread(i)
            break
        except:
            threads[0].join()

for thread in threads:
    thread.join()
    threads.remove(thread)





# Sort the responses based on ip
responses = sorted(responses, key=itemgetter(0))

newResponses = [] # Make a list for the sorted devices
rept = [] # Make a list for the found repeaters

# Fill the 'beautifultable' with the sorted responses and add the found repeaters to 'rept'
for i in responses:
    newi = list(i)
    newi[0] = '192.168.178.' + str(newi[0])

    newResponses.append(tuple(newi))
    if(newi[1].startswith(repeaterMacStart)):
        rept.append(newi)





# If not all devices are found send an email with all of the information
if(len(rept) != 4): #len(repeaterMac)):

    # Creating a connection to the smtp server and login
    s = smtplib.SMTP(host='smtp.gmail.com', port=587)
    s.starttls()
    s.login(MY_ADDRESS, PASSWORD)

    # Create the message to send
    msg = MIMEMultipart()
    msg['From']=MY_ADDRESS
    msg['To']=receiver
    msg['Subject']=subject

    # Filling a 'beautifultable' with the found repeaters
    table = BeautifulTable()
    table.columns.header = ['IP', 'MAC', 'Response Code', 'Vendor']
    for i in rept:
        table.rows.append(i)

    # Filling a 'beautifultable' with the found devices
    allTable = BeautifulTable()
    allTable.columns.header = ['IP', 'MAC', 'Response Code', 'Vendor']
    for i in newResponses:
        allTable.rows.append(i)

    # Save the tables to filename
    text_file = open(filename, "w")
    text_file.write('Repeaters found:\n' + str(table) + '\n\n\nAll devices found:\n' + str(allTable))
    text_file.close()

    # Add the file to the email as attachment
    attachment = MIMEText(open(filename).read())
    attachment.add_header('Content-Disposition', 'attachment', filename=filename)
    msg.attach(attachment)

    # Find out which mac addresses are missing
    result = []
    for t in rept:
        result.append(t[1])
    result = set(result)
    missing = repeaterMac.symmetric_difference(result)
    message = 'Expected 3 repeaters but only found ' + str(len(rept)) + '\nMissing: ' + str(missing)
    msg.attach(MIMEText(message, 'plain'))

    # Finally send the message
    s.send_message(msg)

    # Delete the log
    os.unlink(filename)

    # Finish up
    del msg
    s.quit()
