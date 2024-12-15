import re
import sqlite3
import subprocess
import sys
from tabulate import tabulate

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

class Database:
    def __init__(self, knownTableName, unknownTableName):
        self.connection = sqlite3.connect('arp.db')
        self.connection.row_factory = self.dict_factory
        self.cursor = self.connection.cursor()

        self.knownTableName = knownTableName
        self.unknownTableName = unknownTableName

    def dict_factory(self, cursor, row):
        return {cursor.description[i][0]: row[i] for i in range(len(row))}

    def getNotInEntry(self):
        arpResult = self.networker.getArp()

        for arpDict in arpResult:
            arpMac = arpDict['mac']

            if arpMac not in self.knownEntry.getAllList('mac') and arpMac not in self.unknownEntry.getAllList('mac'):
                print(arpMac)

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

    def getCursor(self):
        return self.cursor

    def getConnection(self):
        return self.connection

    def getKnownTableName(self):
        return self.knownTableName

    def getUnknownTableName(self):
        return self.unknownTableName

class Command:
    def execute(self):
        pass

class HelpCommand(Command):
    @staticmethod
    def execute():
        help_text = """
Usage: python script.py [COMMAND] [OPTIONS]

Commands:
    -s [known|unknown]    Show all entries from the specified table (known or unknown).
    -u [known|unknown]    Update the specified table (known or unknown) based on ARP scan.
    -i [known|unknown]    Insert a new entry into the specified table (known or unknown).
                        For known: provide 'name' and 'mac'.
                        For unknown: provide 'ip' and 'mac'.
    -d [known|unknown]    Delete a row from the specified table (known or unknown) by column value.
                        Specify the column name and value for deletion.

Examples:
    python script.py -s known       # Display entries from the 'known' table.
    python script.py -u unknown     # Update the 'unknown' table based on ARP scan.
    python script.py -i known 'Device1' '00:1A:2B:3C:4D:5E'  # Insert a known entry with name and MAC.
    python script.py -d unknown ip '192.168.1.100'  # Delete an unknown entry based on IP address.

Notes:
    - The ARP scan is used to update the IP addresses for known MAC addresses.
    - The program works with a SQLite database, and changes are saved persistently.
        """
        print(help_text)

    @staticmethod
    def insert():
        print("""
-i [known|unknown]    Insert a new entry into the specified table (known or unknown).
    For known: provide 'name' and 'mac'.
    For unknown: provide 'ip' and 'mac'.
            """)

class UpdateCommand(Command):
    def __init__(self, knownTable, unknownTable, networker):
        self.tableUpdater = TableUpdater(knownTable, unknownTable, networker)

    def execute(self, args=None):
        if not args:
            self.tableUpdater.updateKnownEntry()
            self.tableUpdater.updateUnknownEntry()

        elif args[0] == 'known':
            self.tableUpdater.updateKnownEntry()

        elif args[0] == 'unknown':
            self.tableUpdater.updateUnknownEntry()

class SelectCommand(Command):
    def __init__(self, knownTable, unknownTable):
        self.knownTable = knownTable
        self.unknownTable = unknownTable

    def execute(self, args=None):
        if not args:
            self.unknownTable.select()
            self.knownTable.select()

        elif args[0] == 'known':
            self.knownTable.select()

        elif args[0] == 'unknown':
            self.unknownTable.select()

class InsertCommand(Command):
    def __init__(self, knownTable, unknownTable):
        self.knownTable = knownTable
        self.unknownTable = unknownTable

    def execute(self, args):
        try:
            table = args[0]
            nameIp = args[1]
            mac = args[2]

            if table == 'known':
                self.knownTable.insertRow(nameIp, mac)
            elif table == 'unknown':
                self.unknownTable.insertRow(nameIp, mac)

        except Exception as e:
            HelpCommand.insert()
            print(f'Invalid args: {e}')

class CommandDispatcher:
    def __init__(self, database):
        self.knownTable = Table(database.getKnownTableName(), 1, database.getCursor(), database.getConnection())
        self.unknownTable = Table(database.getUnknownTableName(), 0, database.getCursor(), database.getConnection())

        self.networker = Networker()

        self.commands = {
            '-u': UpdateCommand(self.knownTable, self.unknownTable, self.networker),
            '-s': SelectCommand(self.knownTable, self.unknownTable),
            '-i': InsertCommand(self.knownTable, self.unknownTable),
            '-h': HelpCommand()
        }

    def dispatch(self):
        sysArgs = sys.argv
        if len(sysArgs) > 1:
            command = sysArgs[1]
            
            if command in self.commands:
                commandClass = self.commands[command]
            else:
                print(f'Unknown command: {command}')
                return 1

            args = None if not len(sysArgs) > 2 else sysArgs[2:len(sysArgs)]

            if args:
                commandClass.execute(args)
            else:
                commandClass.execute()

        else:
            print("Missing command.")

def main():
    database = Database('knownEntries', 'unknownEntries')
    database.createTables()

    commandDispatcher = CommandDispatcher(database)
    commandDispatcher.dispatch()

if __name__ == '__main__':
    main()