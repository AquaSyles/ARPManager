import re
import sqlite3
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
    def __init__(self, tableName, isKnownTable, cursor, connection):
        self.tableName = tableName
        self.isKnownTable = isKnownTable

        self.cursor = cursor
        self.connection = connection

    def getAllEntry(self): # None -> [{'x': x}, {'x', x}]
        self.cursor.execute(f"SELECT * FROM {self.tableName}")
        entries = self.cursor.fetchall()

        return entries

    def getAllList(self, column):  # ip | mac | name -> ['x', 'x']
        outputList = []
        for columnItem in self.getAllEntry():
            if column in columnItem:
                outputList.append(columnItem[column])
            else:
                raise KeyError(f"Column '{column}' does not exist in table '{self.tableName}' entries.")
        return outputList

    def select(self):
        entries = self.getAllEntry()
        print(tabulate(entries))

    def validateMac(self, mac: str) -> bool:
        if mac in self.getAllList('mac'):
            print('Duplicate MAC Address')
            return False

        macRegex = '^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$'
        if not bool(re.match(macRegex, mac)):
            print('Invalid MAC Address')
            return False

        return True

    def insertRow(self, nameIp, mac) -> None:
        mac = mac.replace(' ', '')
        if self.isKnownTable:
            try:
                if self.validateMac(mac):
                    self.cursor.execute(f"INSERT INTO {self.tableName} (name, mac) VALUES (?, ?)", (nameIp, mac))
            except Exception as error:
                print("Error when inserting query @insertRow:", error)
                return 1

        elif not self.isKnownTable:
            try:
                if self.validateMac(mac):
                    self.cursor.execute(f"INSERT INTO {self.tableName} (ip, mac) VALUES (?, ?)", (nameIp, mac))
            except Exception as error:
                print("Error when inserting query @insertRow:", error)
                return 1

        self.connection.commit()

    def updateColumnValueById(self, column: str, value: str, id: int) -> None:
        print(f'Parameters: column -> {column}, value -> {value}, id -> {id}')

        command = f"UPDATE {self.tableName} SET {column}=? WHERE id=?"
        print(f'Query: {command}')

        self.cursor.execute(command, (value, id))
        self.connection.commit()

    def updateMacById(self, mac, id):
        self.updateColumnValueById('mac', mac, id)
    
    def deleteRowByColumn(self, column, value) -> None:
        try:
            self.cursor.execute(f"DELETE FROM {self.tableName} WHERE {column}=?", (value,))
            self.connection.commit()
        except Exception as e:
            print(f"Error in deleteRowByColumn: {e}")

class DatabaseManager:
    def __init__(self, knownTableName, unknownTableName):
        self.connection = sqlite3.connect('arp.db')
        self.connection.row_factory = self.dict_factory
        self.cursor = self.connection.cursor()

        self.networker = Networker()

        self.knownEntry = Table(knownTableName, 1, self.cursor, self.connection)
        self.unknownEntry = Table(unknownTableName, 0, self.cursor, self.connection)

    def dict_factory(self, cursor, row):
        return {cursor.description[i][0]: row[i] for i in range(len(row))}

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
                    self.unknownEntry.insertRow(arpDict['ip'], arpDict['mac'])

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
                self.unknownEntry.deleteRowByColumn('mac', unknownEntryMac)
                print(f"Deleted duplicate IP: {unknownEntryMac}")

    def createTables(self):
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS knownEntries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            mac TEXT NOT NULL UNIQUE,
            ip TEXT,
            time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')

        self.cursor.execute('''CREATE TABLE IF NOT EXISTS unknownEntries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip TEXT NOT NULL,
            mac TEXT NOT NULL UNIQUE,
            time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')

        self.connection.commit()

    def execute(self):
        if len(sys.argv) > 1:
            command = sys.argv[1]

            match command:
                case "-s":
                    try:
                        parameter = sys.argv[2]
                        
                        if parameter == 'known':
                            self.knownEntry.select()
                        elif parameter =='unknown':
                            self.unknownEntry.select()
                        else:
                            print('Incorrect table as parameter.')

                    except:
                        self.unknownEntry.select()
                        self.knownEntry.select()
                    
                case "-u":
                    try:
                        parameter = sys.argv[2]

                        if parameter == "known":
                            self.updateKnownEntry()
                        elif parameter == "unknown":
                            self.updateUnknownEntry()
                    
                    except:
                        self.update()

                case "-i":
                    try:
                        table = sys.argv[2]

                        if table == 'known':
                            name = sys.argv[3]
                            mac = sys.argv[4]

                            self.knownEntry.insertRow(name, mac)
                        elif table == 'unknown':
                            ip = sys.argv[3]
                            mac = sys.argv[4]

                            self.unknownEntry.insertRow(ip, mac)

                    except:
                        print("Incorrect flags")

                case "-d":
                    try:
                        table = sys.argv[2]
                        column = sys.argv[3]
                        value = sys.argv[4]

                        if table == 'known':
                            self.knownEntry.deleteRowByColumn(column, value)
                        elif table == 'unknown':
                            self.unknownEntry.deleteRowByColumn(column, value)

                    except:
                        print("Incorrect flags")
        else:
            print('Missing flags')

def main():
    databaseManager = DatabaseManager(knownTableName='knownEntries', unknownTableName='unknownEntries')
    databaseManager.createTables()
    databaseManager.execute()

    

if __name__ == '__main__':
    main()

# To Do
# Make it so it deletes 3 days old unknoMacEntries, this works because we will update all unknownEntries on update call instead of only inserting new unknown entries.