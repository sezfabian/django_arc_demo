# ARC Pay API (Django)

Local Django API with three endpoints:

- `/api/free/`
- `/api/cheap/`
- `/api/expensive/`

## Quick funding checklist

Before running paid endpoint tests:

1. Create or choose a buyer wallet (`ARC_PAY_BUYER_ADDRESS` + `BUYER_PRIVATE_KEY`).
2. Fund the buyer on Arc testnet.
3. Deposit buyer USDC into **Circle Gateway**.
4. Confirm `.env` has valid Circle credentials and matching network values.
5. Run `scripts/call_local_endpoints.py` against your running local server.

Notes:

- Paid API calls use the buyer's **Gateway balance**.
- No gas is required per API request for Gateway-paid calls.
- If Gateway has no balance for buyer, paid routes usually fail with `402`.

## 1) Prerequisites

- Python 3.11+ (project currently uses a local `.venv`)
- `pip`

## 2) Create and activate virtual environment

From the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

Install project dependencies in your environment (if you already have them, this is not required).  
At minimum, this project needs Django and `django_x402_arc` for the endpoint test script.

```bash
pip install django
pip install "django-arc-pay @ git+https://github.com/sezfabian/django_x402_arc.git"
```

## 3) Configure environment variables

Create a `.env` file in the project root with the keys below:

```env
# Circle Console Credentials
CIRCLE_API_KEY=
CIRCLE_ENTITY_SECRET=

# Seller Details
ARC_PAY_SELLER_ADDRESS=

# Buyer Details
ARC_PAY_BUYER_ADDRESS=
BUYER_PRIVATE_KEY=

# Network Config
ARC_RPC_URL=https://arc-testnet.drpc.org
CHAIN_ID=5042002
# Optional in runtime, defaults to arcTestnet:
# ARC_PAY_NETWORK=arcTestnet
```

These values are loaded by `core/settings.py` and used by API/payment flows and the local test caller script.

## 4) Run database migrations

```bash
python manage.py migrate
```

## 5) Run the server

```bash
python manage.py runserver
```

Server default URL:

- `http://127.0.0.1:8000`

Available routes:

- `GET /api/free/`
- `GET /api/cheap/`
- `GET /api/expensive/`

## 6) Run the local endpoint test script with logs

In a second terminal (keep server running in the first terminal):

```bash
source .venv/bin/activate
python scripts/call_local_endpoints.py --base-url http://127.0.0.1:8000 --log-file run1.md
```

What this script does:

- Calls `/api/free/` 5 times
- Calls `/api/cheap/` 50 times
- Calls `/api/expensive/` 10 times
- Prints each attempt in console
- Appends a Markdown log report to the file set by `--log-file`

Useful custom options:

```bash
python scripts/call_local_endpoints.py \
  --base-url http://127.0.0.1:8000 \
  --env-file .env \
  --log-file endpoint_call_log.md \
  --chain arcTestnet \
  --free 5 \
  --cheap 50 \
  --expensive 10
```

## 7) Troubleshooting

- `Missing BUYER_PRIVATE_KEY...`  
  Ensure `.env` contains `BUYER_PRIVATE_KEY`.
- `Missing ARC_PAY_BUYER_ADDRESS...`  
  Ensure `.env` contains `ARC_PAY_BUYER_ADDRESS`.
- Connection errors while running the script  
  Ensure `python manage.py runserver` is active and `--base-url` is correct.
- Failed transactions (`402`), insufficient funds, or payment errors  
  Ensure the buyer wallet is funded on the configured network and Circle credentials are valid.

## 8) Requirements and wallet funding

Runtime requirements for successful paid endpoint calls:

- Valid Circle credentials in `.env`:
  - `CIRCLE_API_KEY`
  - `CIRCLE_ENTITY_SECRET`
- Network settings:
  - `ARC_RPC_URL` (defaults to Arc testnet URL in this README)
  - `ARC_PAY_NETWORK` (optional, defaults to `arcTestnet` in `core/settings.py`)
- Wallet variables:
  - `ARC_PAY_SELLER_ADDRESS` (address receiving payments)
  - `ARC_PAY_BUYER_ADDRESS` and `BUYER_PRIVATE_KEY` (wallet used by `scripts/call_local_endpoints.py`)

Wallet roles and funding:

- **Seller wallet (`ARC_PAY_SELLER_ADDRESS`)**
  - Receives payments from paid endpoints (`/api/cheap/`, `/api/expensive/`).
  - Usually does not need additional balance for local API serving; it is the recipient address.
- **Buyer wallet (`ARC_PAY_BUYER_ADDRESS` + `BUYER_PRIVATE_KEY`)**
  - Pays for requests made by the local test script.
  - Must be funded on the same network configured in `.env`.
  - Funds must be deposited into **Circle Gateway** for this buyer address (wallet balance alone is not enough for gateway payments).
  - Needs enough balance to cover repeated calls (for default run plan, enough to pay all cheap/expensive attempts plus buffer for retries/fees).

Important payment behavior:

- Paid API requests are deducted from the buyer's **Gateway balance**.
- For these Gateway-paid requests, you do **not** need to send gas for each API call.
- If Gateway has no balance for the buyer, paid routes will fail (often as `402`).

Funding guidance:

- Use a wallet/faucet/source compatible with your selected Arc network.
- Confirm funds are on the same chain as `ARC_RPC_URL` / `ARC_PAY_NETWORK`.
- Deposit the buyer funds into Circle Gateway, then re-run the endpoint script.
- If you see frequent `402` responses, top up/deposit buyer funds to Gateway first.

Deposit helper command:

```bash
python3 scripts/deposit_gateway.py --amount 10
```

Using the buyer wallet helper script you added:

```bash
source .venv/bin/activate
python scripts/gen_buyer_wallet.py
```

Optional: append generated key directly to `.env`:

```bash
python scripts/gen_buyer_wallet.py --append-dotenv
```

After generating a buyer wallet:

1. Set/update `ARC_PAY_BUYER_ADDRESS` and `BUYER_PRIVATE_KEY` in `.env`.
2. Fund that buyer on Arc testnet (for example via Circle faucet).
3. Deposit USDC for that buyer into Circle Gateway.
4. Run:

```bash
python scripts/call_local_endpoints.py --base-url http://127.0.0.1:8000 --log-file run1.md
```

