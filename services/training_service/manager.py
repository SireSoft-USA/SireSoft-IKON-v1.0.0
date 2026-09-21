class TrainingJobManager:
    def __init__(self, factory=None):
        self.factory = TrainingFactory() if factory is None else factory
        self._jobs = {}
        self._order = []

    def create_job(self, job_id, config):
        if not isinstance(job_id, str) or job_id == "":
            raise ValueError("job_id must be non-empty str")
        if job_id in self._jobs:
            raise ValueError("training job already exists: " + job_id)

        job = self.factory.create(job_id, config)
        self._jobs[job_id] = job
        self._order.append(job_id)
        return job

    def get(self, job_id):
        if job_id not in self._jobs:
            raise KeyError("training job not found: " + str(job_id))
        return self._jobs[job_id]

    def list_jobs(self):
        return [
            self._jobs[job_id].summary()
            for job_id in self._order
        ]

    def remove_job(self, job_id):
        job = self.get(job_id)

        if job.status == "training":
            raise RuntimeError("cannot remove a job while training")

        del self._jobs[job_id]
        self._order = [
            item for item in self._order
            if item != job_id
        ]
        return job

    def train_step(self, job_id, sequences):
        job = self.get(job_id)
        batch = job.batch_builder.build(sequences)

        if batch.batch_size() == 0:
            raise ValueError("training step produced an empty batch")

        job.begin_training()

        try:
            metrics = job.trainer.train_batch(batch)
            metrics["batch_size"] = batch.batch_size()
            metrics["sequence_length"] = batch.sequence_length()
            job.record("train_step", metrics)
            job.end_training()
            return metrics

        except Exception as error:
            job.fail(str(error))
            raise

    def train_epoch(self, job_id, sequence_batches):
        job = self.get(job_id)
        batches = []

        for sequences in sequence_batches:
            batch = job.batch_builder.build(sequences)
            if batch.batch_size() > 0:
                batches.append(batch)

        if len(batches) == 0:
            raise ValueError(
                "training epoch requires at least one non-empty batch"
            )

        job.begin_training()

        try:
            metrics = job.trainer.train_epoch(batches)
            job.record("train_epoch", metrics)
            job.end_training()
            return metrics

        except Exception as error:
            job.fail(str(error))
            raise

    def evaluate(self, job_id, sequence_batches):
        job = self.get(job_id)
        batches = []

        for sequences in sequence_batches:
            batch = job.batch_builder.build(sequences)
            if batch.batch_size() > 0:
                batches.append(batch)

        if len(batches) == 0:
            raise ValueError(
                "evaluation requires at least one non-empty batch"
            )

        metrics = job.evaluator.evaluate(batches)
        improved = job.trainer.record_validation_loss(metrics["loss"])
        metrics["improved_best"] = improved
        metrics["best_validation_loss"] = (
            job.trainer.state.best_validation_loss
        )
        job.record("evaluation", metrics)
        return metrics

    def save_checkpoint(self, job_id, path, metadata=None):
        job = self.get(job_id)

        if metadata is None:
            metadata = {}
        if not isinstance(metadata, dict):
            raise TypeError("metadata must be dict or None")

        combined = {
            "job_id": job.job_id,
            "job_status": job.status,
            "job_config": job.config,
        }

        for key in metadata:
            combined[key] = metadata[key]

        info = job.checkpoint_manager.save(
            path=path,
            model=job.model,
            optimizer=job.optimizer,
            scheduler=job.scheduler,
            trainer=job.trainer,
            metadata=combined,
        )

        job.checkpoints.append(dict(info))
        job.record("checkpoint_save", info)
        return info

    def load_checkpoint(self, job_id, path):
        job = self.get(job_id)

        payload = job.checkpoint_manager.load(
            path=path,
            model=job.model,
            optimizer=job.optimizer,
            scheduler=job.scheduler,
            trainer=job.trainer,
            strict_model=True,
        )

        job.restore_ready()

        metrics = {
            "path": path,
            "global_step": job.trainer.state.global_step,
            "epoch": job.trainer.state.epoch,
            "metadata": payload.get("metadata", {}),
        }

        job.record("checkpoint_load", metrics)
        return metrics

    def complete(self, job_id):
        job = self.get(job_id)
        job.complete()
        return job.summary()
