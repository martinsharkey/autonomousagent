import pytest
import json
import shutil
from pathlib import Path

from core.learning import TrajectoryAnalyzer, LearningEngine, learn_from_session, analyze_agent_trajectories
from core.data_logger import log_trajectory


class TestTrajectoryAnalyzer:
    def setup_method(self):
        self.agent_name = "autobot"
        self.session_id = "test_learning_session"
        self.learning_dir = Path("learning") / self.agent_name
        self.trajectory_dir = Path("trajectories") / self.session_id
        
        if self.learning_dir.exists():
            shutil.rmtree(self.learning_dir)
        if self.trajectory_dir.exists():
            shutil.rmtree(self.trajectory_dir)
        
        log_trajectory("autobot", {}, "prompt1", "response1", 0.8, session_id=self.session_id)
        log_trajectory("autobot", {}, "prompt2", "response2", 0.3, session_id=self.session_id)
        log_trajectory("autobot", {}, "prompt1", "response3", 0.9, session_id=self.session_id)
    
    def teardown_method(self):
        if self.learning_dir.exists():
            shutil.rmtree(self.learning_dir)
        if self.trajectory_dir.exists():
            shutil.rmtree(self.trajectory_dir)
    
    def test_analyzer_initialization(self):
        analyzer = TrajectoryAnalyzer(self.agent_name)
        assert analyzer.agent_name == self.agent_name
        assert analyzer.learning_dir.exists()
    
    def test_analyze_trajectories(self):
        analyzer = TrajectoryAnalyzer(self.agent_name)
        analysis = analyzer.analyze_trajectories(self.session_id, min_reward=0.5)
        
        assert analysis["agent"] == self.agent_name
        assert analysis["session_id"] == self.session_id
        assert analysis["total_trajectories"] == 3
        assert len(analysis["successful"]) == 2
        assert len(analysis["failed"]) == 1
        assert len(analysis["recommendations"]) > 0
    
    def test_extract_patterns(self):
        analyzer = TrajectoryAnalyzer(self.agent_name)
        analysis = analyzer.analyze_trajectories(self.session_id)
        
        patterns = analysis["patterns"]
        assert len(patterns) > 0
        
        prompt_patterns = [p for p in patterns if p["type"] == "prompt_pattern"]
        assert len(prompt_patterns) > 0
    
    def test_generate_recommendations(self):
        analyzer = TrajectoryAnalyzer(self.agent_name)
        analysis = analyzer.analyze_trajectories(self.session_id)
        
        recommendations = analysis["recommendations"]
        assert len(recommendations) > 0
        assert any("performance" in rec.lower() for rec in recommendations)
    
    def test_get_learning_history(self):
        analyzer = TrajectoryAnalyzer(self.agent_name)
        analyzer.analyze_trajectories(self.session_id)
        
        history = analyzer.get_learning_history(limit=10)
        assert len(history) == 1
        assert history[0]["agent"] == self.agent_name


class TestLearningEngine:
    def setup_method(self):
        self.session_id = "test_engine_session"
        self.learning_dir = Path("learning")
        self.trajectory_dir = Path("trajectories") / self.session_id
        
        if self.learning_dir.exists():
            shutil.rmtree(self.learning_dir)
        if self.trajectory_dir.exists():
            shutil.rmtree(self.trajectory_dir)
        
        self.messages_dir = Path("messages")
        if self.messages_dir.exists():
            shutil.rmtree(self.messages_dir)
        
        log_trajectory("autobot", {}, "p1", "r1", 0.8, session_id=self.session_id)
        log_trajectory("alpha_evaluator", {}, "p2", "r2", 0.9, session_id=self.session_id)
        log_trajectory("beta_worker", {}, "p3", "r3", 0.7, session_id=self.session_id)
    
    def teardown_method(self):
        if self.learning_dir.exists():
            shutil.rmtree(self.learning_dir)
        if self.trajectory_dir.exists():
            shutil.rmtree(self.trajectory_dir)
        if self.messages_dir.exists():
            shutil.rmtree(self.messages_dir)
        
        from core.learning import _learning_engine
        import core.learning
        core.learning._learning_engine = None
        
        from core.communication import _message_bus
        import core.communication
        core.communication._message_bus = None
    
    def test_engine_initialization(self):
        engine = LearningEngine()
        assert engine.learning_dir.exists()
    
    def test_learn_from_session(self):
        engine = LearningEngine()
        results = engine.learn_from_session(self.session_id)
        
        assert "autobot" in results
        assert "alpha_evaluator" in results
        assert "beta_worker" in results
        
        assert results["autobot"]["total_trajectories"] == 1
        assert results["alpha_evaluator"]["total_trajectories"] == 1
    
    def test_get_session_learning(self):
        engine = LearningEngine()
        engine.learn_from_session(self.session_id)
        
        session_data = engine.get_session_learning(self.session_id)
        assert session_data is not None
        assert session_data["session_id"] == self.session_id
    
    def test_get_learning_summary(self):
        engine = LearningEngine()
        engine.learn_from_session(self.session_id)
        
        summary = engine.get_learning_summary()
        assert summary["total_sessions"] == 1
        assert len(summary["agents_learned"]) == 3


class TestLearningFunctions:
    def setup_method(self):
        self.session_id = "test_functions_session"
        self.learning_dir = Path("learning")
        self.trajectory_dir = Path("trajectories") / self.session_id
        
        if self.learning_dir.exists():
            shutil.rmtree(self.learning_dir)
        if self.trajectory_dir.exists():
            shutil.rmtree(self.trajectory_dir)
        
        self.messages_dir = Path("messages")
        if self.messages_dir.exists():
            shutil.rmtree(self.messages_dir)
        
        log_trajectory("autobot", {}, "p1", "r1", 0.8, session_id=self.session_id)
    
    def teardown_method(self):
        if self.learning_dir.exists():
            shutil.rmtree(self.learning_dir)
        if self.trajectory_dir.exists():
            shutil.rmtree(self.trajectory_dir)
        if self.messages_dir.exists():
            shutil.rmtree(self.messages_dir)
        
        from core.learning import _learning_engine
        import core.learning
        core.learning._learning_engine = None
        
        from core.communication import _message_bus
        import core.communication
        core.communication._message_bus = None
    
    def test_learn_from_session_function(self):
        results = learn_from_session(self.session_id)
        assert "autobot" in results
    
    def test_analyze_agent_trajectories_function(self):
        analysis = analyze_agent_trajectories("autobot", self.session_id)
        assert analysis["agent"] == "autobot"
        assert analysis["total_trajectories"] == 1
