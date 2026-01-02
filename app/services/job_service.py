from app.repositories import job_repository
from app.domain.job import Job

def create_job(printer_ip, zpl, loja):
    job = Job(printer_ip, zpl, loja)
    return job_repository.save(job)

def mark_job_result(job_id, success):
    job = job_repository.find_by_id(job_id)
    if not job:
        return None

    if success:
        job.mark_success()
    else:
        job.mark_failed()

    return job
