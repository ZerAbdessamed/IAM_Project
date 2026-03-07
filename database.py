import mysql.connector

def connect():
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="ymTUfp3g.", 
        database="university"
    )
    
    return conn