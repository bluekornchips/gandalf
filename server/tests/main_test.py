"""Test suite for main.py server implementation."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from main import GandalfServer


class TestGandalfServer:
    """Test suite for GandalfServer class."""

    def setup_method(self) -> None:
        """Set up test fixtures before each test method."""
        self.server = GandalfServer()

    def test_server_initialization(self) -> None:
        """Test that server initializes correctly with all required components."""
        assert self.server.server is not None
        assert self.server.server.name == "Gandalf"
        assert self.server.tool_registry is not None

    @pytest.mark.asyncio
    async def test_server_run_method(self) -> None:
        """Test that server run method calls the underlying server run method."""
        with patch.object(self.server.server, "run") as mock_run:
            await self.server.run()
            mock_run.assert_called_once()

    def test_server_capabilities(self) -> None:
        """Test that server has required capabilities configured."""
        from src.config.constants import SERVER_CAPABILITIES

        assert "tools" in SERVER_CAPABILITIES
        assert "logging" in SERVER_CAPABILITIES
        assert SERVER_CAPABILITIES["tools"]["listChanged"] is True

    @pytest.mark.asyncio
    async def test_echo_tool(self) -> None:
        """Test echo tool functionality with various inputs."""
        server = GandalfServer()

        result = await server.tool_registry.execute_tool("echo", {"message": "Hello"})
        assert result[0].text == "Echo: Hello"

        result = await server.tool_registry.execute_tool("echo", {"message": ""})
        assert result[0].text == "Echo: "

        result = await server.tool_registry.execute_tool("echo", None)
        assert result[0].text == "Echo: "

    @pytest.mark.asyncio
    async def test_server_info_tool(self) -> None:
        """Test server info tool returns expected server information."""
        server = GandalfServer()

        result = await server.tool_registry.execute_tool("get_server_info", {})

        assert "Gandalf" in result[0].text
        assert "0.1.0" in result[0].text

    @pytest.mark.asyncio
    async def test_unknown_tool(self) -> None:
        """Test that unknown tool calls return appropriate error message."""
        server = GandalfServer()

        result = await server.tool_registry.execute_tool("unknown_tool", {})

        assert "Unknown tool: unknown_tool" in result[0].text

    @pytest.mark.asyncio
    async def test_concurrent_tool_calls(self) -> None:
        """Test that server can handle multiple concurrent tool calls."""
        server = GandalfServer()
        tasks = [
            server.tool_registry.execute_tool("echo", {"message": f"Message {i}"})
            for i in range(5)
        ]

        results = await asyncio.gather(*tasks)

        assert len(results) == 5
        for i, result in enumerate(results):
            assert f"Echo: Message {i}" in result[0].text


class TestMainFunction:
    """Test suite for main function."""

    @patch("main.GandalfServer")
    @patch("main.asyncio.run")
    def test_main_success(
        self, mock_asyncio_run: MagicMock, mock_server_class: MagicMock
    ) -> None:
        """Test successful execution of main function."""
        mock_server = MagicMock()
        mock_server_class.return_value = mock_server
        from main import main

        main()

        mock_server_class.assert_called_once()
        mock_asyncio_run.assert_called_once_with(mock_server.run())

    @patch("main.GandalfServer")
    @patch("main.asyncio.run")
    @patch("main.sys.exit")
    def test_main_keyboard_interrupt(
        self,
        mock_exit: MagicMock,
        mock_asyncio_run: MagicMock,
        mock_server_class: MagicMock,
    ) -> None:
        """Test main function handles KeyboardInterrupt gracefully."""
        mock_server = MagicMock()
        mock_server_class.return_value = mock_server
        mock_asyncio_run.side_effect = KeyboardInterrupt()
        from main import main

        main()

        mock_exit.assert_called_once_with(0)

    @patch("main.GandalfServer")
    @patch("main.asyncio.run")
    @patch("main.sys.exit")
    def test_main_general_exception(
        self,
        mock_exit: MagicMock,
        mock_asyncio_run: MagicMock,
        mock_server_class: MagicMock,
    ) -> None:
        """Test main function handles general exceptions with proper exit code."""
        mock_server = MagicMock()
        mock_server_class.return_value = mock_server
        mock_asyncio_run.side_effect = Exception("Test error")
        from main import main

        main()

        mock_exit.assert_called_once_with(1)
