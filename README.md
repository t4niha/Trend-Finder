Python 3.12.4 is recommended

To set up the database on your computer:

1. Open the project terminal and run this to install required packages:
   pip install -r requirements.txt

2. Download and install PostgreSQL if you don’t have it:
   https://www.postgresql.org/download/
   During setup, set a password for your PostgreSQL superuser

3. In the following files, replace the password in the psycopg2.connect calls with your own PostgreSQL password:
   database_util.py (line 8)
   translation.py (line 16)

4. Obtain the file service_account.json for Google Cloud Translation API and store it locally inside the project folder 
   (WARNING: Do NOT commit this file to Github)

5. Run the scripts in order:
   database_util.py (creates the database and imports the CSV)
   translation.py (translates non-English posts into English)