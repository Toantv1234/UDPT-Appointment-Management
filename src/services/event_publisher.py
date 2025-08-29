import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime, date
import pika
from config.settings import settings

logger = logging.getLogger(__name__)

class RabbitMQEventPublisher:
    """Service để publish events tới RabbitMQ"""

    def __init__(self):
        self.connection = None
        self.channel = None
        self._setup_connection()

    def _setup_connection(self):
        """Thiết lập kết nối RabbitMQ"""
        try:
            # RabbitMQ connection parameters
            connection_params = pika.ConnectionParameters(
                host=settings.rabbitmq.host,
                port=settings.rabbitmq.port,
                virtual_host=settings.rabbitmq.virtual_host,
                credentials=pika.PlainCredentials(
                    settings.rabbitmq.username,
                    settings.rabbitmq.password
                ) if settings.rabbitmq.username else None,
                heartbeat=600,
                blocked_connection_timeout=300,
            )

            self.connection = pika.BlockingConnection(connection_params)
            self.channel = self.connection.channel()

            # Declare exchanges và queues
            self._setup_exchanges_and_queues()

            logger.info("RabbitMQ connection established successfully")

        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            self.connection = None
            self.channel = None

    def _setup_exchanges_and_queues(self):
        """Thiết lập exchanges và queues"""
        try:
            # Declare exchange cho appointment events
            self.channel.exchange_declare(
                exchange='appointment.events',
                exchange_type='topic',
                durable=True
            )

            # Declare queue cho confirmed appointments
            self.channel.queue_declare(
                queue='appointment.confirmed',
                durable=True,
                arguments={'x-message-ttl': 86400000}  # TTL 24 hours
            )

            # Declare queue cho cancelled appointments (that were previously confirmed)
            self.channel.queue_declare(
                queue='appointment.cancelled',
                durable=True,
                arguments={'x-message-ttl': 86400000}  # TTL 24 hours
            )

            # Bind queues với routing keys
            self.channel.queue_bind(
                exchange='appointment.events',
                queue='appointment.confirmed',
                routing_key='appointment.confirmed'
            )

            self.channel.queue_bind(
                exchange='appointment.events',
                queue='appointment.cancelled',
                routing_key='appointment.cancelled'
            )

            logger.info("RabbitMQ exchanges and queues setup completed")

        except Exception as e:
            logger.error(f"Failed to setup RabbitMQ exchanges/queues: {e}")
            raise

    def publish_appointment_confirmed_today(self, appointment_data: Dict[str, Any]):
        """
        Publish event khi appointment được confirm (PENDING → CONFIRMED)

        Args:
            appointment_data: Dữ liệu appointment đã được confirm
        """
        if not self._is_connection_healthy():
            logger.warning("RabbitMQ connection unhealthy, attempting to reconnect...")
            self._setup_connection()

        if not self.channel:
            logger.error("Cannot publish event: RabbitMQ connection not available")
            return False

        try:
            # Prepare event message
            event_message = {
                "event_type": "appointment_confirmed",
                "timestamp": datetime.now().isoformat(),
                "source_service": "appointment-management",
                "data": {
                    "appointment_id": appointment_data["id"],
                    "patient_id": appointment_data["patient_id"],
                    "patient_name": appointment_data["patient_name"],
                    "doctor_id": appointment_data["doctor_id"],
                    "doctor_name": appointment_data["doctor_name"],
                    "department_id": appointment_data["department_id"],
                    "department_name": appointment_data["department_name"],
                    "appointment_date": appointment_data["appointment_date"].isoformat() if isinstance(appointment_data["appointment_date"], date) else appointment_data["appointment_date"],
                    "appointment_time": appointment_data["appointment_time"].strftime("%H:%M:%S") if hasattr(appointment_data["appointment_time"], 'strftime') else str(appointment_data["appointment_time"]),
                    "reason": appointment_data["reason"],
                    "is_emergency": appointment_data["is_emergency"],
                    "confirmed_at": appointment_data.get("confirmed_at").isoformat() if appointment_data.get("confirmed_at") else None,
                    "confirmed_by": appointment_data.get("confirmed_by")
                }
            }

            # Publish message
            self.channel.basic_publish(
                exchange='appointment.events',
                routing_key='appointment.confirmed',
                body=json.dumps(event_message, ensure_ascii=False),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Make message persistent
                    content_type='application/json',
                    message_id=f"appointment_confirmed_{appointment_data['id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    timestamp=int(datetime.now().timestamp())
                )
            )

            logger.info(f"Published appointment confirmed event for appointment_id: {appointment_data['id']}")
            return True

        except Exception as e:
            logger.error(f"Failed to publish appointment confirmed event: {e}")
            return False

    def publish_appointment_cancelled(self, appointment_data: Dict[str, Any]):
        """
        Publish event khi appointment được hủy NHƯNG TRƯỚC ĐÓ ĐÃ CONFIRMED (CONFIRMED → CANCELLED)

        Args:
            appointment_data: Dữ liệu appointment bị hủy
        """
        if not self._is_connection_healthy():
            self._setup_connection()

        if not self.channel:
            logger.error("Cannot publish event: RabbitMQ connection not available")
            return False

        try:
            event_message = {
                "event_type": "appointment_cancelled",
                "timestamp": datetime.now().isoformat(),
                "source_service": "appointment-management",
                "data": {
                    "appointment_id": appointment_data["id"],
                    "patient_id": appointment_data["patient_id"],
                    "patient_name": appointment_data["patient_name"],
                    "doctor_id": appointment_data["doctor_id"],
                    "doctor_name": appointment_data["doctor_name"],
                    "department_id": appointment_data["department_id"],
                    "department_name": appointment_data["department_name"],
                    "appointment_date": appointment_data["appointment_date"].isoformat() if isinstance(appointment_data["appointment_date"], date) else appointment_data["appointment_date"],
                    "appointment_time": appointment_data["appointment_time"].strftime("%H:%M:%S") if hasattr(appointment_data["appointment_time"], 'strftime') else str(appointment_data["appointment_time"]),
                    "reason": appointment_data["reason"],
                    "is_emergency": appointment_data["is_emergency"],
                    "cancelled_by": appointment_data.get("cancelled_by"),
                    "cancelled_at": appointment_data.get("cancelled_at"),
                    "cancellation_reason": appointment_data.get("cancellation_reason"),
                    "was_previously_confirmed": True  # Always true for this event type
                }
            }

            self.channel.basic_publish(
                exchange='appointment.events',
                routing_key='appointment.cancelled',
                body=json.dumps(event_message, ensure_ascii=False),
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    content_type='application/json',
                    message_id=f"appointment_cancelled_{appointment_data['id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                )
            )

            logger.info(f"Published appointment cancelled event for appointment_id: {appointment_data['id']}")
            return True

        except Exception as e:
            logger.error(f"Failed to publish appointment cancelled event: {e}")
            return False

    def _is_connection_healthy(self) -> bool:
        """Kiểm tra connection RabbitMQ có healthy không"""
        try:
            return (self.connection and
                    not self.connection.is_closed and
                    self.channel and
                    not self.channel.is_closed)
        except Exception:
            return False

    def close(self):
        """Đóng connection RabbitMQ"""
        try:
            if self.channel and not self.channel.is_closed:
                self.channel.close()
            if self.connection and not self.connection.is_closed:
                self.connection.close()
            logger.info("RabbitMQ connection closed")
        except Exception as e:
            logger.error(f"Error closing RabbitMQ connection: {e}")

    def __del__(self):
        """Destructor để đảm bảo connection được đóng"""
        self.close()

# Singleton instance
_event_publisher: Optional[RabbitMQEventPublisher] = None

def get_event_publisher() -> RabbitMQEventPublisher:
    """Get singleton event publisher instance"""
    global _event_publisher
    if _event_publisher is None:
        _event_publisher = RabbitMQEventPublisher()
    return _event_publisher