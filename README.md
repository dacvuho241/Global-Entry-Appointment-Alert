pip install pytest pytest-mock python-dotenv pytz requests urllib3
```

## Configuration

Copy `.env.example` to `.env` and configure your settings:
```bash
cp .env.example .env
```

Edit `.env` file with your preferences:

```env
# Required Configuration
LOCATION_IDS=14321,5140,5143  # Comma-separated location IDs

# Available Location IDs:
# 14321 - Charlotte International Airport - 5501 Josh Birmingham Parkway Charlotte NC 28208
# 5140 - JFK International Airport - JFK International Airport Terminal 4 Queens NY 11430
# 5142 - Boston Logan Airport - Terminal E East Boston MA 02128
# 5182 - Daniel K. Inouye International Airport - 300 Rodgers Blvd Honolulu HI 96819
# 5002 - Los Angeles International Airport - 380 World Way Los Angeles CA 90045
# 5446 - San Francisco International Airport - San Francisco International Airport San Francisco CA 94128
# 5177 - Seattle-Tacoma International Airport - SeaTac Airport SeaTac WA 98158
# 5013 - Miami International Airport - 4200 NW 21st Street Miami FL 33122
# 5300 - Minneapolis Saint Paul Airport - 4300 Glumack Drive St. Paul MN 55111
# 5447 - Philadelphia International Airport - Terminal A West Philadelphia PA 19153
# 5027 - Detroit International Airport - 601 Rouge Street Building 499 Detroit MI 48242
# 5499 - Champlain-Highgate - 237 West Service Road Highgate Springs VT 05460
# 5161 - Alcan - PO Box 109525 Alcan AK 99515
# 13321 - Chicago O'Hare - 10000 Bessie Coleman Drive Chicago IL 60666

# Optional Configuration
CHECK_INTERVAL=900  # Time between checks in seconds (default: 900)
NTFY_TOPIC=your_topic  # ntfy.sh topic for notifications (create your own at ntfy.sh)
```

## Usage

Run the monitor with:

```bash
python main.py -l LOCATION_ID -n ntfy -t YOUR_NTFY_TOPIC -i CHECK_INTERVAL
```

Example:
```bash
python main.py -l 14321 -n ntfy -t your_topic -i 900