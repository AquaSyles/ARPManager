import re
import sqlite3
import subprocess
import sys
import os
from tabulate import tabulate
from datetime import datetime, timedelta
from commands import *

class MacValidator:
    @staticmethod
    def validate(mac):
        macRegex = '^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$'
        return bool(re.match(macRegex, mac))

class Networker:
    def __init__(self):
        self.arpCache = None

    def getArp(self):
        if self.arpCache:
            output = self.arpCache
            self.__resetCache()
            return output
        else:
            return self.__arp()

    def __arp(self):
        arpScanResult = subprocess.run(
            ['sudo', 'arp-scan', '-l', '-q'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE).stdout.decode()

        self.arpCache = self.__convertToDict(arpScanResult)

        return self.arpCache
    
    def __convertToDict(self, arpInput):
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

    def __resetCache(self):
        self.arpCache = None

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

    def insertRow(self, nameIp, mac) -> None:
        mac = mac.replace(' ', '')

        if MacValidator.validate(mac):
            try:
                if self.isKnownTable:
                    self.cursor.execute(f"INSERT INTO {self.tableName} (name, mac) VALUES (?, ?)", (nameIp, mac))
                elif not self.isKnownTable:
                    self.cursor.execute(f"INSERT INTO {self.tableName} (ip, mac) VALUES (?, ?)", (nameIp, mac))
    
                self.connection.commit()

            except Exception as e:
                print(f'Error when inserting query @insertRow: {e}')

        else:
            print('Invalid MAC address @insertRow')

    def updateColumnValueById(self, column: str, value: str, id: int) -> None:
        try:
            self.cursor.execute(f"UPDATE {self.tableName} SET {column}=? WHERE id=?", (value, id))
            self.connection.commit()

        except Exception as e:
            print(f'Error when inserting query @updateColumnValueById: {e}') 

    def updateColumnValueByColumn(self, whereColumn, whereValue, column, value) -> None:
        try:
            if column == 'mac':
                if not MacValidator.validate(value):
                    print("Invalid MAC Address")
                    return 0

            self.cursor.execute(f"UPDATE {self.tableName} SET {column}=? WHERE {whereColumn}=?", (value, whereValue))
            self.connection.commit()

        except Exception as e:
            print(f'Error when inserting query @updateColumnValueById: {e}') 

    def updateMacById(self, mac, id):
        self.updateColumnValueById('mac', mac, id)
    
    def deleteRowByColumn(self, column, value) -> None:
        try:
            self.cursor.execute(f"DELETE FROM {self.tableName} WHERE {column}=?", (value,))
            self.connection.commit()
        except Exception as e:
            print(f"Error in deleteRowByColumn: {e}")

class TableUpdater:
    def __init__(self, knownTable, unknownTable, networker):
        self.knownEntry = knownTable
        self.unknownEntry = unknownTable
        self.networker = networker

    def update(self) -> None:
        self.updateKnownEntry()
        self.updateUnknownEntry()

    def updateKnownEntry(self) -> None:
        knownEntries = self.knownEntry.getAllEntry()
        arpResult = self.networker.getArp()
        
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
        arpResult = self.networker.getArp()

        for arpDict in arpResult:
            arpMac = arpDict['mac']
            if arpMac not in knownEntriesMacList and arpMac not in unknownEntriesMacList:
                    self.unknownEntry.insertRow(arpDict['ip'], arpDict['mac'])

        self.deleteDuplicateEntry()

    def deleteDuplicateEntry(self) -> None:
        knownEntriesMacList = self.knownEntry.getAllList('mac')
        unknownEntriesMacList = self.unknownEntry.getAllList('mac')

        for unknownMac in unknownEntriesMacList:
            if unknownMac in knownEntriesMacList:
                self.unknownEntry.deleteRowByColumn('mac', unknownMac)

    def deleteOldUnknownEntry(self) -> None:
        unknownEntryList = self.unknownEntry.getAllEntry()

        for unknownEntryDict in unknownEntryList:
            
            unknownEntryTime = datetime.strptime(unknownEntryDict['time'], "%Y-%m-%d %H:%M:%S")
            currentTime = datetime.now()
            timeDelta = timedelta(days=2)

            if unknownEntryTime < currentTime - timeDelta: # unknown entry was made more than timeDelta minutes ago
                self.unknownEntry.deleteRowByColumn('id', unknownEntryDict['id'])

class Database:
    def __init__(self, databasePath, knownTableName, unknownTableName):
        self.connection = sqlite3.connect(databasePath)
        self.connection.row_factory = self.dict_factory
        self.cursor = self.connection.cursor()

        self.knownTableName = knownTableName
        self.unknownTableName = unknownTableName

    def dict_factory(self, cursor, row):
        return {cursor.description[i][0]: row[i] for i in range(len(row))}

    def getCursor(self):
        return self.cursor

    def getConnection(self):
        return self.connection

    def getKnownTableName(self):
        return self.knownTableName

    def getUnknownTableName(self):
        return self.unknownTableName

    # def getNotInEntry(self):
    #     arpResult = self.networker.getArp()

    #     for arpDict in arpResult:
    #         arpMac = arpDict['mac']

    #         if arpMac not in self.knownEntry.getAllList('mac') and arpMac not in self.unknownEntry.getAllList('mac'):
    #             print(arpMac)

    def createTables(self):
        self.cursor.execute(f'''CREATE TABLE IF NOT EXISTS {self.knownTableName} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            mac TEXT NOT NULL UNIQUE,
            ip TEXT,
            time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')

        self.cursor.execute(f'''CREATE TABLE IF NOT EXISTS {self.unknownTableName} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip TEXT NOT NULL,
            mac TEXT NOT NULL UNIQUE,
            time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')

        self.connection.commit()

def main():
    databasePath = os.path.join(os.path.dirname(__file__), 'arp.db')
    database = Database(databasePath, 'knownEntries', 'unknownEntries')
    database.createTables()

    commandDispatcher = CommandDispatcher(database, Table, Networker, TableUpdater)
    commandDispatcher.dispatch()

if __name__ == '__main__':
    main()