# CIT-U CampusPass

### Web-Based Visitor Management System

CIT-U CampusPass is a web-based visitor management system developed to replace the university’s manual visitor logbook with a modern, digital process. The system streamlines campus entry by allowing visitors to pre-register online or register directly on-site. Administrators and guards can monitor visits in real time, manage records, and generate analytical reports to enhance campus security and operational efficiency.

---

## Tech Stack

| Layer                    | Technology                                            |
| ------------------------ | ----------------------------------------------------- |
| **Frontend**             | HTML · CSS · JavaScript (Django Templates)            |
| **Backend**              | Python · Django Framework                             |
| **Database**             | Supabase (PostgreSQL)                                 |
| **Environment & Config** | Python Virtual Environment (`venv`) · `python-dotenv` |
| **Version Control**      | Git · GitHub                                          |
| **Additional Tools**     | Email Notifications                                   |

---

## Setup and Run Instructions

```bash
# Clone the Repository
git clone https://github.com/joshnuevas/CSIT327-G1-CIT-UCampusPass.git
cd CSIT327-G1-CIT-UCampusPass

# Install Dependencies
pip install -r requirements.txt

# Apply Migrations
cd CSIT327-G1-CIT-UCampusPass/citu_campuspass
python manage.py migrate

# Run the Development Server
python manage.py runserver
```

---

## Team Members

| Name                  | Role           | CIT-U Email              |
| --------------------- | -------------- | ------------------------ |
| **Josh Anton Nuevas** | Lead Developer | joshanton.nuevas@cit.edu |
| **Melody Ann Garbo**  | Developer      | melodyann.garbo@cit.edu  |
| **Godwin Labaya**     | Developer      | godwin.labaya@cit.edu    |

---

## Deployed Link
