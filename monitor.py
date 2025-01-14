from collections import namedtuple
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3 import Retry

Update = namedtuple("Update", ["price", "price_change", "price_change_percent", "ts"])


class Monitoring:
    BASE_API_ENDPOINT = "https://fapi.binance.com/fapi/v1/ticker/24hr?symbol={symbol}"

    def __init__(
        self,
        session: requests.Session,
        symbol: str,
        percent_threshold: float = 1.0,
        time_interval: int = 3600,
    ):
        self.symbol = symbol.upper()
        self.api_endpoint = self.BASE_API_ENDPOINT.format(symbol=self.symbol)
        self.percent_threshold = percent_threshold
        self.time_interval = time_interval
        self.initial = None
        self.session = session

    def monitor(self) -> None:
        try:
            for update in self.get_prices():
                self.initial = self.initial or update
                if update.ts - self.initial.ts >= self.time_interval:
                    self.compare_prices(self.initial, update)
                    self.initial = update
                self.display_update(update)
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("\nMonitoring stopped by user.")

    def get_prices(self):
        while True:
            try:
                response = self.session.get(self.api_endpoint).json()
                yield Update(
                    price=float(response["lastPrice"]),
                    price_change=float(response["priceChange"]),
                    price_change_percent=float(response["priceChangePercent"]),
                    ts=time.monotonic(),
                )
            except requests.exceptions.RequestException as e:
                raise RuntimeError("Network error: Please try again") from e

    def compare_prices(self, initial: Update, current: Update) -> None:
        percentage_change = 100 * (current.price - initial.price) / initial.price
        if abs(percentage_change) > self.percent_threshold:
            direction = "increased" if percentage_change > 0 else "decreased"
            print(
                f"\nPrice has {direction} by {abs(percentage_change):.2f}% over the period."
            )
        print(f"Current price: {current.price:.2f}\n")

    def display_update(self, update: Update) -> None:
        print(f"Current price: {update.price:.2f}")
        print(f"Change percentage: {update.price_change_percent:.2f}%")
        print(f"Price change: {update.price_change:.2f}")
        print("*" * 20)


def create_retry_session(retries: int, backoff_factor: float = 0.3) -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=[500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def main():
    print("Available symbols: BTCUSDT, ETHUSDT, BNBUSDT, etc.")
    symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]  # Replace with desired default symbols
    symbol = "ETHUSDT"  # Default for environments without interactive input

    # Try to get user input; fallback to default symbol in case of an error
    try:
        user_input = (
            input("Enter the symbol to monitor (e.g., ETHUSDT): ").strip().upper()
        )
        if user_input in symbols:
            symbol = user_input
        else:
            print(f"Invalid symbol. Defaulting to {symbol}.")
    except OSError:
        print(f"Input not supported. Defaulting to {symbol}.")

    session = create_retry_session(retries=5)
    monitor = Monitoring(
        session=session, symbol=symbol, percent_threshold=0.01, time_interval=5
    )
    monitor.monitor()


if __name__ == "__main__":
    main()
