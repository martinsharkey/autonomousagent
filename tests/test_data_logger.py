import pytest
import json
import shutil
from pathlib import Path
from datetime import datetime

from core.data_logger import TrajectoryLogger, get_logger, log_trajectory, get_trajectories, get_training_data


class TestTrajectoryLogger:
    def setup_method(self):
        self.test_session = "test_session_001"
        self.trajectory_dir = Path("trajectories") / self.test_session
        if self.trajectory_dir.exists():
            shutil.rmtree(self.trajectory_dir)
    
    def teardown_method(self):
        if self.trajectory_dir.exists():
            shutil.rmtree(self.trajectory_dir)
    
    def test_logger_initialization(self):
        logger = TrajectoryLogger(self.test_session)
        assert logger.session_id == self.test_session
        assert logger.trajectory_dir.exists()
        assert logger.trajectory_file.exists()
        assert logger.metadata_file.exists()
    
    def test_log_trajectory(self):
        logger = TrajectoryLogger(self.test_session)
        
        trajectory = logger.log_trajectory(
            agent_name="autobot",
            state={"loop_count": 1, "phase": "coordination"},
            prompt="Test prompt",
            response="Test response",
            reward=0.85,
            metadata={"test": True}
        )
        
        assert trajectory["agent"] == "autobot"
        assert trajectory["prompt"] == "Test prompt"
        assert trajectory["response"] == "Test response"
        assert trajectory["reward"] == 0.85
        assert trajectory["metadata"]["test"] is True
        assert "timestamp" in trajectory
    
    def test_get_trajectories(self):
        logger = TrajectoryLogger(self.test_session)
        
        logger.log_trajectory("autobot", {}, "p1", "r1", 0.8)
        logger.log_trajectory("alpha_evaluator", {}, "p2", "r2", 0.9)
        logger.log_trajectory("autobot", {}, "p3", "r3", 0.7)
        
        all_trajectories = logger.get_trajectories()
        assert len(all_trajectories) == 3
        
        autobot_trajectories = logger.get_trajectories(agent_name="autobot")
        assert len(autobot_trajectories) == 2
        
        limited_trajectories = logger.get_trajectories(limit=2)
        assert len(limited_trajectories) == 2
    
    def test_get_training_data(self):
        logger = TrajectoryLogger(self.test_session)
        
        logger.log_trajectory("autobot", {}, "p1", "r1", 0.8)
        logger.log_trajectory("autobot", {}, "p2", "r2", 0.3)
        logger.log_trajectory("autobot", {}, "p3", "r3", 0.9)
        
        all_training = logger.get_training_data()
        assert len(all_training) == 3
        
        filtered_training = logger.get_training_data(min_reward=0.5)
        assert len(filtered_training) == 2
        assert all(t["reward"] >= 0.5 for t in filtered_training)
    
    def test_export_for_training(self):
        logger = TrajectoryLogger(self.test_session)
        
        logger.log_trajectory("autobot", {}, "p1", "r1", 0.8)
        logger.log_trajectory("autobot", {}, "p2", "r2", 0.9)
        
        output_file = self.trajectory_dir / "export.jsonl"
        count = logger.export_for_training(str(output_file), format="jsonl")
        
        assert count == 2
        assert output_file.exists()
        
        with open(output_file, "r") as f:
            lines = f.readlines()
            assert len(lines) == 2


class TestDataLoggerFunctions:
    def setup_method(self):
        self.test_session = "test_session_002"
        self.trajectory_dir = Path("trajectories") / self.test_session
        if self.trajectory_dir.exists():
            shutil.rmtree(self.trajectory_dir)
    
    def teardown_method(self):
        if self.trajectory_dir.exists():
            shutil.rmtree(self.trajectory_dir)
        
        from core.data_logger import _logger_instances
        if self.test_session in _logger_instances:
            del _logger_instances[self.test_session]
    
    def test_get_logger(self):
        logger1 = get_logger(self.test_session)
        logger2 = get_logger(self.test_session)
        assert logger1 is logger2
    
    def test_log_trajectory_function(self):
        trajectory = log_trajectory(
            agent_name="beta_worker",
            state={"test": True},
            prompt="Test",
            response="Response",
            reward=0.75,
            session_id=self.test_session
        )
        
        assert trajectory["agent"] == "beta_worker"
        assert trajectory["reward"] == 0.75
    
    def test_get_trajectories_function(self):
        log_trajectory("autobot", {}, "p1", "r1", 0.8, session_id=self.test_session)
        log_trajectory("alpha_evaluator", {}, "p2", "r2", 0.9, session_id=self.test_session)
        
        trajectories = get_trajectories(session_id=self.test_session)
        assert len(trajectories) == 2
    
    def test_get_training_data_function(self):
        log_trajectory("autobot", {}, "p1", "r1", 0.8, session_id=self.test_session)
        log_trajectory("autobot", {}, "p2", "r2", 0.3, session_id=self.test_session)
        
        training_data = get_training_data(session_id=self.test_session, min_reward=0.5)
        assert len(training_data) == 1
        assert training_data[0]["reward"] == 0.8
