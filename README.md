# Flask Inventory Managment for Open Access IT Assets Management

## IT Asset Management System

### The goal is to create a web application using Flask framework to manage inventory of IT assets deployed in workstations.

## Python, Flask, SQLite3

## Installation

First, you need to clone this repo:

```bash
$ git clone https://github.com/shraite7/flask-inventory-app.git
```

Then change into the `flask-inventory-app` folder:

```bash
$ cd flask-inventory-app
```

Now, we will need to create a virtual environment and install all the dependencies. We have two options available for now.

Use Pipenv:

```bash
$ pipenv install
$ pipenv shell
```

Or use pip + virtualenv:

```bash
$ pip install -r requirements.txt
$ virtualenv venv
$ venv\Scripts\activate (for windows), . venv/bin/activate  (for mac)
```
## How to Run the Application?
**Before running the application, make sure you have activated the virtual enviroment:**

**Make sure to have DB Browser for SQLite3 installed** 

**Make sure to have VSCode installed**

**Make sure to have python installed**
**in the terminal or cmd install these libraries...
> pip install flask 
> pip install pandas 
> pip install flask_login
> pip install datetime
> pip install mariadb
> pip install openpyxl


**Run the application (app.py) in the terminal of VSCode**
```bash 
$ flask run
```
