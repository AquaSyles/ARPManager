import re
import pymysql
import subprocess
import sys
from tabulate import tabulate

class Networker:
    def arp(self):
        arpScanResult = subprocess.run(
            ['sudo', 'arp-scan', '-l', '-q'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE).stdout.decode()

        return self.convertToDict(arpScanResult)
    
    def convertToDict(self, arpInput):
        arpLines = arpInput.splitlines()
        pattern = r'(?P<ip>192\.168\.\d+\.\d+)\s+(?P<mac>[0-9a-fA-F:]{17})'

        arpOutput = []
        for line in arpLines:
            regexResult = re.search(pattern, line)

            if regexResult:
                ip = regexResult.group('ip')
                mac = regexResult.group('mac')

                arpOutput.append({'ip': ip, 'mac': mac})

        return arpOutput

class Table():
    def __init__(self, tableName, cursor, connection):
        self.tableName = tableName
        self.cursor = cursor
        self.connection = connection

    def getAllEntry(self): # None -> [{'x': x}, {'x', x}]
        self.cursor.execute(f"SELECT * FROM {self.tableName}")
        entries = self.cursor.fetchall()

        return entries

    def select(self):
        entries = self.getAllEntry()
        print(tabulate(entries))

    def getAllList(self, column):  # ip | mac | name -> ['x', 'x']
        outputList = []
        for columnItem in self.getAllEntry():
            if column in columnItem:
                outputList.append(columnItem[column])
            else:
                raise KeyError(f"Column '{column}' does not exist in table '{self.tableName}' entries.")
        return outputList

    def validateMac(self, mac: str) -> bool:
        if mac in self.getAllList('mac'):
            print('Duplicate MAC Address')
            return False

        macRegex = '^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$'
        if not bool(re.match(macRegex, mac)):
            print('Invalid MAC Address')
            print(mac)
            return False

        return True

    def insertKnownEntry(self, name: str, mac: str) -> None:
        if not name:
            print("Invalid name.")
            return None

        mac = mac.replace(' ', '') # I remove spaces so that you can't include them.
        isValidMacAddress = self.validateMac(mac)

        if isValidMacAddress:
            try:
                self.cursor.execute(f"""INSERT INTO {self.tableName} (name, mac)
                                    VALUES (%s, %s)""", (name, mac))
            except Exception as error:
                print("Error when inserting query.", error)
            
            self.connection.commit()

    def updateColumnValueById(self, column: str, value: str, id: int) -> None:
        print(f'Parameters: column -> {column}, value -> {value}, id -> {id}')

        command = f"UPDATE {self.tableName} SET {column}=%s WHERE id=%s"
        print(f'Query: {command}')

        self.cursor.execute(command, (value, id))
        self.connection.commit()

    def updateMacById(self, mac, id):
        self.updateColumnValueById('mac', mac, id)

    def delete(self) -> None:
        self.cursor.execute(f"DELETE FROM {self.tableName}")
        self.connection.commit()
    
    def insertUnknownEntry(self, ip, mac) -> None:
        try:
            self.cursor.execute(f"INSERT INTO {self.tableName} (ip, mac) VALUES (%s, %s)", (ip, mac))
            self.connection.commit()

        except:
            print(f"Error when inserting: {Exception}")
        
class DatabaseManager:
    def __init__(self, database, knownTableName, unknownTableName, host, user, password):
        self.connection = pymysql.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            cursorclass=pymysql.cursors.DictCursor
        )

        self.cursor = self.connection.cursor() 

        self.networker = Networker()

        self.knownEntry = Table(knownTableName, self.cursor, self.connection)
        self.unknownEntry = Table(unknownTableName, self.cursor, self.connection)

    def update(self) -> None:
        self.updateKnownEntry()
        self.updateUnknownEntry()
        self.deleteDuplicateEntry()

    def updateKnownEntry(self) -> None:
        knownEntries = self.knownEntry.getAllEntry()
        arpResult = self.networker.arp()
        
        for knownEntry in knownEntries:
            macFound = False
            for arpDict in arpResult:
                if knownEntry['mac'] == arpDict['mac']:
                    macFound = True
                    
                    self.knownEntry.updateColumnValueById('ip', arpDict['ip'], knownEntry['id'])

            if not macFound:
                self.knownEntry.updateColumnValueById('ip', 'NULL', knownEntry['id'])

    def updateUnknownEntry(self) -> None:
        knownEntriesMacList = self.knownEntry.getAllList('mac')
        unknownEntriesMacList = self.unknownEntry.getAllList('mac')
        arpResult = self.networker.arp()

        for arpDict in arpResult:
            arpMac = arpDict['mac']
            if arpMac not in knownEntriesMacList and arpMac not in unknownEntriesMacList:
                    self.unknownEntry.insertUnknownEntry(arpDict['ip'], arpDict['mac'])

    def getNotInEntry(self):
        arpResult = self.networker.arp()

        for arpDict in arpResult:
            arpMac = arpDict['mac']

            if arpMac not in self.knownEntry.getAllList('mac') and arpMac not in self.unknownEntry.getAllList('mac'):
                print(arpMac)

    def deleteDuplicateEntry(self) -> None:
        knownEntryMacList = self.knownEntry.getAllList('mac')
        unknownEntryMacList = self.unknownEntry.getAllList('mac')

        for unknownEntryMac in unknownEntryMacList:
            if unknownEntryMac in knownEntryMacList:
                self.cursor.execute(f"DELETE FROM {self.unknownEntry.tableName} WHERE mac=%s", (unknownEntryMac))
                print(f"Deleted duplicate IP: {unknownEntryMac}")
                self.connection.commit()

def main():
    databaseManager = DatabaseManager(database='arp', knownTableName='knownEntries', unknownTableName='unknownEntries', host='localhost', user='root', password='aqua')
    
    try:
        command = sys.argv[1]

        match command:
            case "-s":
                try:
                    parameter = sys.argv[2]
                    
                    if parameter == 'knownEntry':
                        databaseManager.knownEntry.select()
                    elif parameter =='unknownEntry':
                        databaseManager.unknownEntry.select()
                    else:
                        print('Incorrect table as parameter.')

                except:
                    databaseManager.unknownEntry.select()
                    databaseManager.knownEntry.select()
                
            case "-u":
                try:
                    parameter = sys.argv[2]

                    if parameter == "updateKnownEntry":
                        databaseManager.updateKnownEntry()
                    elif parameter == "unknownEntry":
                        databaseManager.updateUnknownEntry()
                
                except:
                    databaseManager.update()

            case "updateUnknownEntry":
                databaseManager.updateUnknownEntry()
    
    except:
        print('No input given.')

if __name__ == '__main__':
    main()


# To Do
# Make it so it deletes 3 days old unknoMacEntries, this works because we will update all unknownEntries on update call instead of only inserting new unknown entries.
