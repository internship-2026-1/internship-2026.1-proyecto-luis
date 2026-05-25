import logging
import xmlrpc.client

from celery import shared_task
from celery.exceptions import MaxRetriesExceededError
from django.conf import settings
from django.db import transaction as db_transaction

from catalog.odoo import OdooClient, OdooConfigurationError
from orders.models import IntegrationLog, Order

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sync_order_to_odoo(self, order_id):
    try:
        order = (
            Order.objects.using('postgresql_db')
            .prefetch_related('items')
            .get(pk=order_id)
        )
    except Order.DoesNotExist:
        logger.warning('[sync_order_to_odoo] Order not found: %s', order_id)
        return

    request_payload = {
        'order_number': str(order.order_number),
        'customer_id': str(order.customer_id) if order.customer_id else None,
        'total_amount': str(order.total_amount),
        'currency': order.currency,
        'items': [
            {
                'product_sku': item.product_sku,
                'quantity': item.quantity,
                'price_at_purchase': str(item.price_at_purchase),
            }
            for item in order.items.using('postgresql_db').all()
        ],
    }

    log_entry = IntegrationLog(
        order=order,
        status_code='pending',
        raw_request=request_payload,
        raw_response='',
    )

    try:
        client = OdooClient()
        responses = []

        for item in order.items.using('postgresql_db').all():
            product_sku = item.product_sku
            quantity = item.quantity

            products = client._execute(
                'product.product',
                'search_read',
                [[['default_code', '=', product_sku]]],
                {'fields': ['id', 'qty_available'], 'limit': 1},
            )

            if not products:
                response = {'error': f"SKU '{product_sku}' no existe en Odoo."}
                order.status = Order.Status.FAILED
                order.save(using='postgresql_db')
                log_entry.status_code = 'not_found'
                log_entry.raw_response = str(response)
                log_entry.save(using='postgresql_db')
                return response

            odoo_product = products[0]
            current_stock = int(odoo_product.get('qty_available', 0) or 0)
            new_stock = max(current_stock - quantity, 0)

            quants = client._execute(
                'stock.quant',
                'search_read',
                [[
                    ['product_id', '=', odoo_product['id']],
                    ['location_id.usage', '=', 'internal'],
                ]],
                {'fields': ['id', 'quantity'], 'limit': 1},
            )

            if quants:
                quant_id = quants[0]['id']
                write_result = client._execute(
                    'stock.quant',
                    'write',
                    [[quant_id], {'quantity': new_stock}],
                )
                responses.append({
                    'sku': product_sku,
                    'previous_stock': current_stock,
                    'quantity': quantity,
                    'new_stock': new_stock,
                    'write_result': write_result,
                })
            else:
                responses.append({
                    'sku': product_sku,
                    'previous_stock': current_stock,
                    'quantity': quantity,
                    'new_stock': new_stock,
                    'warning': 'No se encontró stock.quant interno. No se actualizó stock.',
                })

        with db_transaction.atomic(using='postgresql_db'):
            order.status = Order.Status.SYNCED
            order.save(using='postgresql_db')
            log_entry.status_code = 'success'
            log_entry.raw_response = str(responses)
            log_entry.save(using='postgresql_db')

        return responses

    except (OdooConfigurationError, Exception) as exc:
        logger.exception('[sync_order_to_odoo] Error syncing order %s: %s', order_id, exc)
        order.status = Order.Status.FAILED
        order.save(using='postgresql_db')
        log_entry.status_code = 'error'
        log_entry.raw_response = str(exc)
        log_entry.save(using='postgresql_db')
        try:
            raise self.retry(exc=exc)
        except MaxRetriesExceededError:
            return {'error': str(exc)}
