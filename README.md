Python 3.12.4 is recommended

To set up the database on your computer:

1. Open the project terminal and run this to install required packages:
   pip install -r requirements.txt

2. Install PostgreSQL and set a password for your superuser: 
   https://www.postgresql.org/download/

3. In the config.py file, replace the password for DB_PASSWORD with your own PostgreSQL password

4. Obtain the file service_account.json for Google Cloud credentials and store it locally inside the project folder 
   (WARNING: Do NOT commit this file to Github)

5. Run the scripts in database.ipnyb