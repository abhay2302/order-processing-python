import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
import asyncio

from app.services.order_service import OrderService

logger = logging.getLogger(__name__)

class OrderStatusUpdater:
    """Background job scheduler for order status updates"""
    
    def __init__(self, order_service: OrderService):
        self.order_service = order_service
        self.scheduler = None
        self._setup_scheduler()
    
    def _setup_scheduler(self):
        """Configure the AsyncIO scheduler"""
        jobstores = {
            'default': MemoryJobStore()
        }
        
        executors = {
            'default': ThreadPoolExecutor(max_workers=2)
        }
        
        job_defaults = {
            'coalesce': True,
            'max_instances': 1,
            'misfire_grace_time': 30
        }
        
        self.scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone='UTC'
        )
        
        # Add event listeners
        self.scheduler.add_listener(self._job_executed, EVENT_JOB_EXECUTED)
        self.scheduler.add_listener(self._job_error, EVENT_JOB_ERROR)
    
    def start(self):
        """Start the scheduler and add jobs"""
        try:
            logger.info("Starting order status updater scheduler...")
            
            # Add the recurring job to update pending orders every 5 minutes
            self.scheduler.add_job(
                func=self._update_pending_orders_job,
                trigger='interval',
                minutes=5,
                id='update_pending_orders',
                name='Update PENDING orders to PROCESSING',
                replace_existing=True
            )
            
            self.scheduler.start()
            logger.info("Order status updater scheduler started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")
            raise e
    
    def stop(self):
        """Stop the scheduler gracefully"""
        if self.scheduler and self.scheduler.running:
            logger.info("Stopping order status updater scheduler...")
            self.scheduler.shutdown(wait=True)
            logger.info("Order status updater scheduler stopped")
    
    def _update_pending_orders_job(self):
        """Job function to update pending orders"""
        try:
            logger.info("Running background job: update pending orders")
            processed_count = self.order_service.process_pending_orders()
            logger.info(f"Background job completed: processed {processed_count} orders")
            
        except Exception as e:
            logger.error(f"Background job failed: {e}")
            raise e
    
    def _job_executed(self, event):
        """Handle job execution events"""
        logger.info(f"Job {event.job_id} executed successfully")
    
    def _job_error(self, event):
        """Handle job error events"""
        logger.error(f"Job {event.job_id} failed: {event.exception}")
    
    def get_job_status(self):
        """Get status of scheduled jobs"""
        if not self.scheduler:
            return {"status": "not_initialized"}
        
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            })
        
        return {
            "status": "running" if self.scheduler.running else "stopped",
            "jobs": jobs
        }
    
    def trigger_job_manually(self, job_id: str = "update_pending_orders"):
        """Manually trigger a job for testing purposes"""
        try:
            if self.scheduler and self.scheduler.running:
                job = self.scheduler.get_job(job_id)
                if job:
                    job.modify(next_run_time=None)  # Run immediately
                    logger.info(f"Job {job_id} triggered manually")
                    return True
                else:
                    logger.warning(f"Job {job_id} not found")
                    return False
            else:
                logger.warning("Scheduler is not running")
                return False
        except Exception as e:
            logger.error(f"Failed to trigger job {job_id}: {e}")
            return False