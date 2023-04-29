import json
import time
from datetime import datetime, timedelta
from binance.client import Client
from binance.exceptions import BinanceAPIException

def load_settings():
    """Загружает настройки из файла settings.json и возвращает их в виде словаря."""
    with open('settings.json') as settings_file:
        settings = json.load(settings_file)
    return settings

def check_api_key(api_key, api_secret):
    """Проверяет подключение к Binance API с помощью переданных ключей API."""
    try:
        client = Client(api_key, api_secret)
        client.get_account()
        return True
    except:
        return False

def cancel_order(client, symbol, order_id):
    """Отменяет ордер с заданным идентификатором."""
    try:
        cancel_response = client.cancel_order(symbol=symbol, orderId=order_id)
        print(f"Cancelled order {order_id}: {cancel_response}")
    except BinanceAPIException as e:
        print(f"Error cancelling order {order_id}: {e}")

def create_orders(client, orders):
    """Создает ордера с заданными параметрами."""
    for order in orders:
        try:
            order_response = client.create_order(
                symbol=order['symbol'],
                side=order['side'],
                type=order['type'],
                timeInForce='GTC',
                price=str(order['price']),
                quantity=str(order['quantity'])
            )
            print(f"Order created: {order_response}")
        except BinanceAPIException as e:
            print(f"Error creating order: {e}")

def main():
    settings = load_settings()

    if not check_api_key(settings['api_key'], settings['api_secret']):
        print("Failed to connect to Binance API. Please check your API key and secret.")
        return
    else:
        print("Connected to Binance API successfully.")

    client = Client(settings['api_key'], settings['api_secret'])

    start_time = datetime.fromisoformat(settings['start_time'])
    time_until_start = start_time - datetime.now()

    if time_until_start.total_seconds() > 0:
        print(f"Waiting {time_until_start.total_seconds()} seconds until start time.")
        time.sleep(int(time_until_start.total_seconds()))

    # Пытаемся создать первоначальный ордер до тех пор, пока он не будет создан
    while True:
        try:
            order = client.create_order(
                symbol=settings['symbol'],
                side=settings['side'],
                type=settings['order_type'],
                timeInForce='GTC',
                price=str(settings['price']),
                quantity=str(settings['quantity'])
            )
            print(f"Order created: {order}")
            break
        except BinanceAPIException as e:
            print(f"Error creating order: {e}")
            time.sleep(int(settings.get('initial_order_retry_interval', 60)))

    order_id = order['orderId']
    order_status = order['status']
    order_price = float(order['price'])
    order_quantity = float(order['origQty'])
    order_created_time = datetime.fromtimestamp(order['transactTime'] / 1000)

    # Если первоначальный ордер исполнен успешно, выводим соответствующее сообщение
    if order_status == 'FILLED':
        print("Order filled successfully.")
    else:
        # Если первоначальный ордер не был исполнен в течение заданного времени, отменяем его и создаем новые ордера
        order_expiration_time = order_created_time + timedelta(seconds=int(settings.get('initial_order_expiration_time', 300)))
        time_until_expiration = order_expiration_time - datetime.now()

        while time_until_expiration.total_seconds() > 0:
            time.sleep(1)
            order_status = client.get_order(symbol=settings['symbol'], orderId=order_id)['status']
            time_until_expiration = order_expiration_time - datetime.now()

            if order_status == 'FILLED':
                print("Order filled successfully.")
                break

        if order_status != 'FILLED':
            print("Order was not filled within the expiration time. Cancelling order and creating new ones.")

            # Отменяем первоначальный ордер и создаем новые ордера из массива orders_after_cancel
            cancel_order(client, settings['symbol'], order_id)

            orders = settings.get('orders_after_cancel', [])

            if len(orders) == 0:
                print("No orders to create after cancelling initial order.")
            else:
                create_orders(client, orders)

    # Ожидаем, пока все ордера не будут исполнены
    time.sleep(int(settings.get('order_execution_interval', 30)))

    # Получаем список открытых ордеров
    open_orders = client.get_open_orders(symbol=settings['symbol'])

    while len(open_orders) > 0:
        time.sleep(int(settings.get('order_execution_interval', 30)))
        open_orders = client.get_open_orders(symbol=settings['symbol'])

    print("All orders executed successfully.")

if __name__ == '__main__':
    main()

