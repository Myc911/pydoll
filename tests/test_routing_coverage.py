import pytest
from unittest.mock import AsyncMock, MagicMock
from pydoll.elements.mixins.find_elements_mixin import FindElementsMixin
from pydoll.interactions.iframe import IFrameContext

class MockElement(FindElementsMixin):
    def __init__(self, handler):
        self._connection_handler = handler
        self._css_only = False

@pytest.mark.asyncio
async def test_describe_node_error_coverage():
    handler = AsyncMock()
    # CDP returns an 'error' key if describeNode fails
    handler.execute_command.return_value = {'error': 'Node not found'}
    el = MockElement(handler)
    
    # This hits line 696: return {}
    result = await el._describe_node('some-id')
    assert result == {}

@pytest.mark.asyncio
async def test_resolve_routing_with_iframe_context_coverage():
    handler = AsyncMock()
    
    iframe_handler = AsyncMock()
    iframe_handler.execute_command.return_value = {'result': {'value': []}}
    
    ctx = IFrameContext(
        frame_id='frame-1',
        session_id='session-1',
        session_handler=iframe_handler
    )
    
    el = MockElement(handler)
    el._iframe_context = ctx
    
    # This hits line 723: return iframe_context.session_handler, ...
    # And line 735: command['sessionId'] = session_id
    cmd = {'method': 'Runtime.evaluate', 'params': {'expression': '1+1'}}
    await el._execute_command(cmd)
    
    assert iframe_handler.execute_command.called
    assert cmd['sessionId'] == 'session-1'

@pytest.mark.asyncio
async def test_resolve_routing_fallback_coverage():
    handler = AsyncMock()
    handler.execute_command.return_value = {'result': {'value': []}}
    
    el = MockElement(handler)
    # No _iframe_context, but has _routing_session_handler
    el._routing_session_handler = handler
    el._routing_session_id = 'routing-session-1'
    
    cmd = {'method': 'Runtime.evaluate', 'params': {'expression': '1+1'}}
    await el._execute_command(cmd)
    
    assert handler.execute_command.called
    assert cmd['sessionId'] == 'routing-session-1'
