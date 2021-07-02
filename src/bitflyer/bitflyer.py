from datetime import datetime
import logging
import time

import dateutil.parser
import pybitflyer

import constants
import settings

logger = logging.getLogger(__name__)

ORDER_COMPLETED = 'COMPLETED'

class Balance(object):
    def __init__(self, currency, available):
        self.currency = currency
        self.available = available

class Ticker(object):
    def __init__(self, product_code, timestamp, bid, ask, volume):
        self.product_code = product_code
        self.timestamp = timestamp
        self.bid = bid
        self.ask = ask
        self.volume = volume

    @property
    def mid_price(self):
        return (self.bid + self.ask) / 2
    

class Order(object):
    def __init__(self, product_code, side, size,
                 child_order_type='MARKET', minute_to_expire=10, child_order_state=None, child_order_acceptance_id=None):
        self.product_code = product_code
        self.side = side
        self.size = size
        self.child_order_type = child_order_type
        self.minute_to_expire = minute_to_expire
        self.child_order_state = child_order_state
        self.child_order_acceptance_id = child_order_acceptance_id

class OrderTimeoutError(Exception):
    """Order timeout error"""
    
class APIClient(object):
    def __init__(self, api_key, api_secret):
        self.api_key = api_key
        self.api_secret = api_secret
        self.client = pybitflyer.API(api_key=api_key, api_secret=api_secret)

    def get_balance(self) -> Balance:
        try:
            resp = self.client.getbalance()
        except Exception as e:
            logger.error(f'action=get_balance error={e}')
            raise
            
        currency = resp[0]['currency_code']
        available = resp[0]['available']
        return Balance(currency, available)

    def get_ticker(self, product_code) -> Ticker:
        try:
            resp = self.client.ticker(product_code=product_code)
        except Exception as e:
            logger.error(f'action=get_ticker error={e}')
            raise
        timestamp = datetime.timestamp(
            dateutil.parser.parse(resp['timestamp']))
        product_code = resp['product_code']
        bid = float(resp['best_bid'])
        ask = float(resp['best_ask'])
        volume = float(resp['volume'])
        return Ticker(product_code, timestamp, bid, ask, volume)

    def send_order(self, order: Order):
#         size = int(order.size*100000000)/100000000
#         try:
#             resp = self.client.sendchildorder(product_code=order.product_code,
#                                      child_order_type=order.child_order_type,
#                                      side=order.side,
#                                      size=size,
#                                      minute_to_expire=order.minute_to_expire)
#             logger.info(f'action=send_order resp={resp}')
#         except Exception as e:
#             logger.error(f'action=send_order error={e}')
#             raise
        resp = {'child_order_acceptance_id': 'JRF20210702-105120-972173'}
        order_id = resp['child_order_acceptance_id']
        order = self.wait_order_complete(order_id)

        if not order:
            logger.error('action=send_order error=timeout')
            raise OrderTimeoutError
        
    def wait_order_complete(self, order_id) -> Order:
        count = 0
        timeout_count = 5
        while True:
            order = self.get_order(order_id)
            if order.child_order_state == ORDER_COMPLETED:
                return order
            time.sleep(1)
            count += 1
            if count > timeout_count:
                return None
            
    def get_order(self, order_id) -> Order:
        try:
            resp = self.client.getchildorders(product_code=settings.product_code,
                                     child_order_acceptance_id=order_id)
            logger.info(f'action=get_order resp={resp}')
        except Exception as e:
            logger.error(f'action=get_order error={e}')
            raise

        order = Order(
            product_code=resp[0]['product_code'],
            side=resp[0]['side'],
            size=float(resp[0]['size']),
            child_order_type=resp[0]['child_order_type'],
            child_order_state=resp[0]['child_order_state'],
            child_order_acceptance_id=resp[0]['child_order_acceptance_id']
        )
        print(order)
        return order