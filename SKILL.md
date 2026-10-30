# NAW Agent Skill

## Project Overview
NAW Agent is a REST API service built with FastAPI.
Purpose:
- Connect Oracle NetSuite Analytics Warehouse (NAW)
- Connect Oracle Autonomous Data Warehouse (ADW)
- Use Oracle Wallet authentication
- Expose business APIs for Open WebUI
- Do NOT allow LLM to generate SQL
- SQL is maintained by developers
Architecture:
User
→ Open WebUI
→ Tool Call
→ NAW Agent API
→ Oracle ADW
→ JSON Response
The LLM never connects directly to Oracle.
The LLM never generates SQL.
The LLM only consumes API responses.
---
## Technology Stack
Python 3.11
FastAPI
oracledb
Pandas
Docker
Oracle Wallet
Open WebUI
Oracle Autonomous Database
---
## Project Structure
app/
├── api/

├── services/

├── repositories/

├── sql/

├── db/

├── core/

├── models/

└── main.py

Responsibilities:
api
    HTTP endpoints only
service
    business logic only
repository
    database access
sql
    SQL files only
db
    connection pool
core
    configuration, logger
models
    request/response models
---
## Coding Rules
### Rule 1
Never write SQL inside FastAPI endpoint.
Bad:
```python
@app.get("/sales")
def sales():

    sql = "select * from sales"

    return run(sql)
```
Good:
```python
@app.get("/sales")
def sales():
    return SalesService.get_sales()
```
### Rule 2
Never write SQL inside Service.
Bad:
```python
class SalesService:
    sql = "select ..."
```
Good:
```python
class SalesService:
    return SalesRepository.get_sales()
```
### Rule 3
SQL must be stored in:

app/sql

Example:

app/sql/customer/top_customer.sql

app/sql/revenue/sales_by_customer.sql

app/sql/inventory/on_hand.sql

---

## Oracle Connection

Use:
oracledb.create_pool()
Connection settings come from .env

Example:

ORACLE_USER

ORACLE_PASSWORD

ORACLE_DSN

WALLET_LOCATION

Never hardcode credentials.

---

## API Standards

Health Check:

GET /api/health

Business APIs:

GET /api/customer/top

GET /api/inventory/onhand

GET /api/revenue/customer

GET /api/ar/aging

GET /api/ap/aging

GET /api/po/open

Response:

{
  "success": true,
  "data": []
}

Error:

{
  "success": false,
  "message": "error message"
}

---

## Repository Pattern

Repository is the only layer allowed to execute SQL.

Example:

CustomerRepository

RevenueRepository

InventoryRepository

---

## SQL Guidelines

Read only.

Allowed:

SELECT

Forbidden:

INSERT

UPDATE

DELETE

MERGE

ALTER

DROP

TRUNCATE

CREATE

Never generate DDL.

Never generate DML.

---

## Logging

Use logger from:

app/core/logger.py

Never use print().

Bad:

print(data)

Good:

logger.info(data)

---

## Open WebUI Integration

Open WebUI calls NAW Agent APIs.

The model should:

- call API
- process JSON
- explain results

The model should not:

- generate SQL
- design schema
- create Oracle queries

---

## New Features

When creating new features:

1. Create SQL file

2. Create Repository

3. Create Service

4. Create API Endpoint

Example:

sql:
app/sql/vendor/vendor_aging.sql

repository:
VendorRepository

service:
VendorService

endpoint:
GET /api/vendor/aging

Follow existing project patterns.

---

## Naming Convention

API

customer.py

inventory.py

vendor.py

Service

CustomerService

InventoryService

VendorService

Repository

CustomerRepository

InventoryRepository

VendorRepository

SQL

customer_balance.sql

open_po.sql

inventory_onhand.sql

---

## Security

Never expose:

ORACLE_PASSWORD

Wallet content

Connection strings

Credentials

Never return stack traces to API users.

Always sanitize exceptions.

---

## Unit Test

Every repository should have test coverage.

tests/

test_customer.py

test_inventory.py

test_po.py

Use pytest.

---

## Important

Assume:

- Oracle Wallet exists
- Connection pool exists
- Repository pattern exists

Always generate code compatible with this architecture.

Always keep SQL in separate files.

Never generate SQL dynamically inside API layer.
