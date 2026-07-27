import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from core.deployer import ComponentSpec, DeploymentPackager, DeploymentManager
from core.mesh_communication import MeshCommunication, MeshNode, NodeStatus
from core.node_monitor import NodeMonitor, MonitorConfig, SpawnStrategy
from deploy.hf_spaces_deployer import HuggingFaceSpacesDeployer
from deploy.replit_deployer import ReplitDeployer
from pathlib import Path
import shutil


class TestComponentSpec:
    def test_component_spec_creation(self):
        spec = ComponentSpec(
            name="test_component",
            description="Test component",
            entry_point="core.test.component"
        )
        assert spec.name == "test_component"
        assert spec.platform == "huggingface_spaces"
        assert spec.timeout_seconds == 30
    
    def test_component_spec_custom_platform(self):
        spec = ComponentSpec(
            name="test_component",
            description="Test component",
            entry_point="core.test.component",
            platform="replit"
        )
        assert spec.platform == "replit"


class TestDeploymentPackager:
    def setup_method(self):
        self.packager = DeploymentPackager(output_dir="deploy/components/test")
    
    def teardown_method(self):
        test_dir = Path("deploy/components/test")
        if test_dir.exists():
            shutil.rmtree(test_dir, ignore_errors=True)
    
    def test_package_hf_spaces(self):
        spec = ComponentSpec(
            name="test_component",
            description="Test component",
            entry_point="core.test.component",
            platform="huggingface_spaces"
        )
        component_dir = self.packager.package(spec)
        assert component_dir.exists()
        assert (component_dir / "app.py").exists()
        assert (component_dir / "requirements.txt").exists()
        assert (component_dir / "Dockerfile").exists()
    
    def test_package_replit(self):
        spec = ComponentSpec(
            name="test_component",
            description="Test component",
            entry_point="core.test.component",
            platform="replit"
        )
        component_dir = self.packager.package(spec)
        assert component_dir.exists()
        assert (component_dir / "main.py").exists()
        assert (component_dir / ".replit").exists()
    
    def test_package_generic(self):
        spec = ComponentSpec(
            name="test_component",
            description="Test component",
            entry_point="core.test.component",
            platform="custom"
        )
        component_dir = self.packager.package(spec)
        assert component_dir.exists()
        assert (component_dir / "app.py").exists()
        assert (component_dir / "Dockerfile").exists()


class TestDeploymentManager:
    def setup_method(self):
        self.manager = DeploymentManager()
    
    def teardown_method(self):
        test_dir = Path("deploy/components")
        if test_dir.exists():
            shutil.rmtree(test_dir, ignore_errors=True)
    
    def test_deploy_creates_record(self):
        spec = ComponentSpec(
            name="test_component",
            description="Test component",
            entry_point="core.test.component"
        )
        deployment = self.manager.deploy(spec)
        assert deployment["component"] == "test_component"
        assert deployment["status"] == "packaged"
        assert "node_id" in deployment
    
    def test_get_deployment(self):
        spec = ComponentSpec(
            name="test_component",
            description="Test component",
            entry_point="core.test.component"
        )
        self.manager.deploy(spec)
        deployment = self.manager.get_deployment("test_component")
        assert deployment is not None
        assert deployment["component"] == "test_component"
    
    def test_list_deployments(self):
        spec = ComponentSpec(
            name="test_component",
            description="Test component",
            entry_point="core.test.component"
        )
        self.manager.deploy(spec)
        deployments = self.manager.list_deployments()
        assert "test_component" in deployments


class TestHFSpacesDeployer:
    def test_deploy_without_token(self):
        """Deployer should work without token for packaging only."""
        deployer = HuggingFaceSpacesDeployer(hf_token=None)
        spec = ComponentSpec(
            name="test_component",
            description="Test component",
            entry_point="core.test.component",
            platform="huggingface_spaces"
        )
        deployment = deployer.deploy(spec)
        assert deployment["component"] == "test_component"
        assert deployment["platform"] == "huggingface_spaces"
        assert "space_name" in deployment
    
    def test_get_status(self):
        deployer = HuggingFaceSpacesDeployer()
        status = deployer.get_status("test-space")
        assert status["space_name"] == "test-space"
        assert status["platform"] == "huggingface_spaces"


class TestReplitDeployer:
    def test_deploy_without_token(self):
        """Deployer should work without token for packaging only."""
        deployer = ReplitDeployer(replit_token=None)
        spec = ComponentSpec(
            name="test_component",
            description="Test component",
            entry_point="core.test.component",
            platform="replit"
        )
        deployment = deployer.deploy(spec)
        assert deployment["component"] == "test_component"
        assert deployment["platform"] == "replit"
        assert "repl_name" in deployment
    
    def test_get_status(self):
        deployer = ReplitDeployer()
        status = deployer.get_status("test-repl")
        assert status["repl_name"] == "test-repl"
        assert status["platform"] == "replit"


class TestMeshCommunication:
    @pytest.mark.asyncio
    async def test_register_node(self):
        mesh = MeshCommunication(council_callback_url="http://localhost:8000/api/mesh/result")
        try:
            node = MeshNode(
                node_id="test-001",
                component="sentiment_analyzer",
                platform="huggingface_spaces",
                url="http://localhost:8000",
                status=NodeStatus.HEALTHY
            )
            result = await mesh.register_node(node)
            assert result["status"] == "registered"
            assert result["node_id"] == "test-001"
        finally:
            await mesh.close()
    
    @pytest.mark.asyncio
    async def test_unregister_node(self):
        mesh = MeshCommunication()
        try:
            node = MeshNode(
                node_id="test-001",
                component="sentiment_analyzer",
                platform="huggingface_spaces",
                url="http://localhost:8000"
            )
            await mesh.register_node(node)
            result = await mesh.unregister_node("test-001")
            assert result["status"] == "unregistered"
        finally:
            await mesh.close()
    
    @pytest.mark.asyncio
    async def test_send_task(self):
        mesh = MeshCommunication()
        try:
            node = MeshNode(
                node_id="test-001",
                component="sentiment_analyzer",
                platform="huggingface_spaces",
                url="http://localhost:8000",
                status=NodeStatus.HEALTHY
            )
            await mesh.register_node(node)
            
            with patch.object(mesh.client, 'post') as mock_post:
                mock_response = Mock()
                mock_response.raise_for_status = Mock()
                mock_response.json = Mock(return_value={"result": "ok"})
                mock_post.return_value = mock_response
                
                result = await mesh.send_task("test-001", {"text": "hello"})
                assert result["status"] == "submitted"
        finally:
            await mesh.close()
    
    @pytest.mark.asyncio
    async def test_get_mesh_status(self):
        mesh = MeshCommunication()
        try:
            node = MeshNode(
                node_id="test-001",
                component="sentiment_analyzer",
                platform="huggingface_spaces",
                url="http://localhost:8000",
                status=NodeStatus.HEALTHY
            )
            await mesh.register_node(node)
            status = mesh.get_mesh_status()
            assert status["total_nodes"] == 1
            assert status["healthy_nodes"] == 1
        finally:
            await mesh.close()


class TestNodeMonitor:
    @pytest.mark.asyncio
    async def test_start_stop(self):
        mesh = MeshCommunication()
        try:
            config = MonitorConfig(
                health_check_interval_seconds=5,
                failure_threshold=2
            )
            monitor = NodeMonitor(mesh, config)
            await monitor.start()
            assert monitor.running is True
            await monitor.stop()
            assert monitor.running is False
        finally:
            await mesh.close()
    
    @pytest.mark.asyncio
    async def test_get_mesh_status(self):
        mesh = MeshCommunication()
        try:
            config = MonitorConfig(
                health_check_interval_seconds=5,
                failure_threshold=2
            )
            monitor = NodeMonitor(mesh, config)
            status = monitor.get_mesh_status()
            assert "monitoring" in status
            assert "mesh" in status
            assert status["monitoring"] is False  # Not started yet
        finally:
            await mesh.close()
