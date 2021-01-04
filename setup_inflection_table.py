import gzip
import sqlite3
import os
import re
import urllib.request

# Download and uncompress Flexion DB SQL dump
gzipped_data = urllib.request.urlopen("https://www.korrekturen.de/flexion/download/nomen.sql.gz").read()
data = gzip.decompress(gzipped_data)

# Init SQLite DB
os.unlink("nomen.sqlite")
db = sqlite3.connect("nomen.sqlite")

# Convert (MySQL → SQLite) and import SQL dump
for command in re.split(";\n|\n\n", data.decode("utf-8")):
    if command.startswith("LOCK TABLES") or command.startswith("UNLOCK TABLES"):
        continue

    elif command.startswith("CREATE TABLE"):
        new_command = ""
        columns = []

        for line in command.split("\n"):
            line = line.strip()

            if line.startswith("CREATE TABLE"):
                new_command += f"{line}\n"

            elif line.startswith("`"): # field - adapt data types
                line_fields = line.split(" ")
                column, datatype = line_fields[0], line_fields[1].split("(")[0].upper()
                rest = "PRIMARY KEY" if column == "`id`" else ""

                SQLITE_DATATYPE_MAP={"VARCHAR": "TEXT", "INT": "INTEGER"}
                if datatype in SQLITE_DATATYPE_MAP:
                    datatype = SQLITE_DATATYPE_MAP[datatype]

                columns.append(f"{column} {datatype} {rest}")
                
            elif line.startswith("PRIMARY KEY") or line.startswith("KEY"): # ignore keys
                continue

            elif line.startswith(")"): # remove engine definition etc. ; now is the time to add columns
                new_command += ",\n".join(columns)
                new_command += ")"

        command = new_command
    
    db.execute(command)

# Finish SQLite setup
db.execute("COMMIT")
db.execute("CREATE INDEX fi ON nomen(form COLLATE NOCASE)")
db.execute("CREATE INDEX fil ON nomen(lemma)")
db.execute("VACUUM")
db.close()