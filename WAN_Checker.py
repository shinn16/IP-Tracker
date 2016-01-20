#! /usr/bin/python3
"""
@author Patrick Shinn
@version 4.3
Last Update: 1/20/16

This program is set up for all operating systems by setting adjustment.
If run on Linux, please add the following to the very top of the file:
#! /usr/bin/python3
This program is a wan checker for a server that will email me with the new IP address anytime
the server IP changes. This is setup to use a gmail server. It will then add theses changes to
the owncloud config.php file. Use the setup.py file to generate settings before using this program.
"""
from time import sleep
import datetime
import smtplib
import os

# initial variables
done = False  # universal boolean for loops
now = datetime.datetime.now()
old = ''  # stores old wan


# Reading settings file and applying settings
settingsList = []
findLocal = os.getcwd()
findLocal = findLocal.strip("'\"\t\n")
try:  # Linux/OSX settings file location
    settingsFile = findLocal + "/settings.txt"
    settings = open(settingsFile, 'r')
    for setting in settings:
        if setting.startswith('#'):
            pass
        else:
            setting = setting.rstrip('\n')
            settingsList.append(setting)
except FileNotFoundError:  # Windows settings file location
    settingsFile = findLocal + '\\settings.txt'
    settings = open(settingsFile, 'r')
    for setting in settings:
        if setting.startswith('#'):
            pass
        else:
            setting = setting.rstrip('\n')
            settingsList.append(setting)

# Settings
#############################################################################################
# OS cli command for wan ip extraction
command = ''
system = settingsList[9]
if system.lower() == 'windows':
    command = 'nslookup myip.opendns.com resolver1.opendns.com'  # untested widows command
elif system.lower() == 'linux':
    command = 'dig TXT +short o-o.myaddr.l.google.com @ns1.google.com'  # linux cli command
elif system.lower() == 'osx':
    command = 'dig TXT +short o-o.myaddr.l.google.com @ns1.google.com'  # OSX cli command

# File locations
phpFile = settingsList[0]           # path to owncloud config.php
oldWanLocation = settingsList[2]    # path to old wan file
logFile = settingsList[1]           # path to log file

# Email Settings
TO = settingsList[3]                # email recipient
FROM = settingsList[4]              # sender email
SUBJECT = settingsList[6]           # email subject
PASSWORD = settingsList[5]          # sender email
EMAIL_SERVER = settingsList[7]      # server address
PORT_NUMBER = settingsList[8]       # server port number
# End Settings
#############################################################################################

# Files opened
oldWan = open(oldWanLocation, 'r')  # file containing the old WAN IP
log = open(logFile, 'a')          # log file

# Function definitions for this program
############################################################################################


def wan_check(cli_command, log_file):
    """
    :param cli_command: cli command for wan ip extraction
    :param log_file: file used to log errors that occur during wan dig
    :return: returns the current wan ip
    """
    read = ''  # stores read from loop.
    while not done:  # continues until IP can be procured
        check = os.popen(cli_command)
        read = check.read()
        if read == ';; connection timed out; no servers could be reached':
            log_file.write('WAN Error: ' + str(read) + ' reattempting. \n')
            sleep(5)
            continue
        elif read == '':
            log_file.write('WAN Error: ' + str(read) + ' reattempting. \n')
            sleep(5)
            continue
        elif read == "dig: couldn't get address for 'ns1.google.com': not found":
            log_file.write('WAN Error: ' + str(read) + ' reattempting. \n')
            sleep(5)
            continue
        elif read == ' ':
            log_file.write('WAN Error: ' + str(read) + ' reattempting. \n')
            sleep(5)
            continue
        else:
            break
    return read


def php_config(current_ip, php_location):
    """
    :param current_ip: ip to be written to owncloud config.php
    :param php_location: path to owncloud config.php
    """
    line_number = 0
    line_store = []
    current_ip = current_ip.strip('\n"')
    config = open(php_location, 'r')
    for line in config:
        if line_number != 8:
            line_store.append(line)
        else:
            line_store.append("    1 => '" + current_ip + "'," + '\n')
        line_number += 1
    config.close()
    config_rewrite = open(php_location, 'w+')
    for line in line_store:
        config_rewrite.write(line)
    config_rewrite.close()


def send_mail(log_txt, current_ip, sender, recipient, sub, passwrd, server_address, server_port):
    """
    :param log_txt: log for errors
    :param current_ip: what the ip to be sent is
    :param sender: sender email address
    :param recipient: receiving email address
    :param sub: subject of email
    :param passwrd: password of sender email
    :param server_address: address of the server
    :param server_port: server port being used
    :return:

    This function takes the various inputs and email the new server ip address to the receiving address
    """
    mail_error = 0
    log_txt.write('\nThe Server IP changed to: ' + current_ip + ' on ' + str(now) + '\n')
    msg = 'Your Server IP Address has changed to: ' + current_ip
    body = '\r\n'.join([
        'To: %s' % recipient,
        'From: %s' % sender,
        'Subject: %s' % sub,
        '',
        msg])

    while not done:
        if mail_error != 10:
            try:
                server = smtplib.SMTP(server_address, server_port)
                server.ehlo()
                server.starttls()
                server.ehlo()
                log_txt.write("Successful connection to server. \n")
                break
            except (ConnectionError, ConnectionRefusedError, ConnectionAbortedError, ConnectionResetError) as error:
                log_txt.write("Connection to server failed: '" + error + "', trying again. \n")
                mail_error += 1
                sleep(5)
        elif mail_error == 10:
            log_txt.write("Failed to connect to the server 10 times, cancel sending. Please check your email"
                          "server settings.\n")
            break

    mail_error -= mail_error  # resets to 0
    while not done:
        if mail_error != 5:
            try:  # email the new ip
                server.login(sender, passwrd)
                server.sendmail(sender, recipient, body)
                log_txt.write('The message was sent successfully. \n \n')
                break
            except (ConnectionError, ConnectionRefusedError, ConnectionAbortedError, ConnectionResetError) as error:
                # if the email is not sent, wait for 5 seconds and try again.
                log_txt.write("Message send Failure: '" + error + "', trying again. \n")
                mail_error += 1
                sleep(5)
        elif mail_error == 5:
            log_txt.write("Failed to log in after 5 attempts, cancel sending. Please check your email settings.\n")
            break

    # Closing all opened files
    log_txt.close()
    server.quit()

# End Definitions
##############################################################################################

# Program start
new = wan_check(command, log)  # sets the new ip to check against.

for ip in oldWan:  # This iterates over the old WAN IP and appends it to the old variable.
    ip.strip('\n')
    old += ip

if new != old:  # if the ip has changed
    # Updates the old wan to the current wan
    oldWan.close()
    oldWan = open(oldWanLocation, 'w')
    oldWan.write(new)
    oldWan.close()

    # php_config function call updates owncloud config.php to accept new wan
    if phpFile.lower() == 'none':  # if the user has no php file, pass this part
        pass
    else:  # else try to use the user config to rewrite it.
        try:  # if the file is found, rewrite it
            php_config(new, phpFile)
        except FileNotFoundError:  # continue the program and send the email
            log.write("php file not found at: " + str(phpFile) + " file not updated")

    # Sends new ip to email
    send_mail(log, new, FROM, TO, SUBJECT, PASSWORD, EMAIL_SERVER, PORT_NUMBER)
    log.close()

else:  # executes if the wan hasn't changed.
    oldWan.close()
    log.close()
    pass  # do nothing