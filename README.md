## Python Quickstart

### Prerequisite

- Python 3.7 or higher
- `pip` version 9.0.1 or higher

### Overview

The Aptos Indexer by Fibonacci Finance is a robust solution for processing and indexing transactions on the Aptos blockchain. This guide covers the setup and execution of the Example Event Processor, which demonstrates how to extract and analyze on-chain data, such as Total Value Locked (TVL), transaction volumes, and slippage metrics.

### Basic Tutorial

1. **Clone the Repository**
   ```bash
   git clone https://github.com/aptos-labs/aptos-indexer-processors
   cd aptos-indexer-processors/python
   ```

2. **Install Dependencies**
   Use `poetry` to install required dependencies:
   ```bash
   poetry install
   ```

3. **Configure Settings**
   Update the `config.yaml` file with the correct indexer settings and database credentials:
   ```bash
   cp config.yaml.example config.yaml
   ```

4. **Define Data Models**
   - Use `models.py` to define data models for the events you want to extract.
   - PostgreSQL is supported, with SQLAlchemy used for ORM-based interactions.

5. **Implement the Processor**
   - Extend `TransactionsProcessor` to parse transactions and save the data to the database.
   - Modify `process_transactions()` to include custom logic for data extraction.

6. **Run the Processor**
   Execute the following command to start indexing:
   ```bash
   poetry run python -m processors.main -c config.yaml
   ```

7. **Run in Docker (Optional)**
   - Use the included `Dockerfile` to build and run the processor.
   - Ensure `config.yaml` is present in the `python` folder:
     ```bash
     docker compose up --build --force-recreate
     ```

8. **Query Indexed Data**
   Use tools like SQLAlchemy to fetch indexed data from the PostgreSQL database for further analysis or integration into your dApp.

---

## Development

### Install Dependencies
```bash
poetry install
```

### Linting & Autoformatting
```bash
poetry run poe pyright  # Type checking
poetry run poe format   # Autoformat using Black
```

### Run Locally in Docker
```bash
docker compose up --build --force-recreate
```

---

## Features

### Comprehensive Metrics
- Extracts data for TVL, transaction volume, and slippage.
- Aggregates 24-hour, weekly, and monthly statistics.

### Real-Time Integrations
- Utilizes the Panora API for live token price updates.

### Protocol Support
- Compatible with protocols like LiquidSwap, ThalaSwap, PancakeSwap, and SushiSwap.
- Expandable to support additional DeFi protocols.

### Robust Deployment
- Deployed on Google Cloud for scalability and reliability.

### Advanced Analytics
- Supports database-ready outputs for use with analytical dashboards and reporting tools.

### Error Handling
- Includes detailed logging and error management for enhanced reliability.

---

## Notes

- Ensure `config.yaml` is properly configured before running.
- PostgreSQL is required for database interactions.
- The example code is designed for educational purposes; customize it for production-grade applications.

For more details about the Aptos Indexer and its features, refer to the [Aptos Indexer Documentation](#).
