## follow
User
 ↓
Open WebUI
 ↓ (Tool Call)
NAW Agent API
 ↓
Oracle ADW / NSAW

## UAT Deployment with Docker Compose

1. Install Git, Docker Engine, and the Docker Compose plugin on the UAT server.
2. Clone this repository and enter the project directory.
3. Copy `.env.example` to `.env` and set the Oracle and OpenAI values. Do not commit `.env`.
4. Transfer the Oracle wallet to the project `wallet/` directory using an approved secure channel. Do not commit the wallet.
5. Start the services:

	```sh
	docker compose up -d --build
	```

6. Check the API:

	```sh
	docker compose ps
	curl http://localhost:8000/api/health
	docker compose logs -f oracle-agent
	```

The API is exposed on port 8000 and Open WebUI on port 3000. Configure firewall rules and TLS through the UAT environment's approved reverse proxy before exposing either service outside the host.

