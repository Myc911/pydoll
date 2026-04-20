import pytest
from unittest.mock import AsyncMock, MagicMock
from pydoll.elements.web_element import WebElement
from pydoll.interactions.iframe import IFrameContext

@pytest.mark.asyncio
async def test_find_elements_mixin_routing_coverage():
    # Setup a real WebElement (which uses FindElementsMixin)
    handler = AsyncMock()
    # Mock describeNode to avoid initialization issues if any
    handler.execute_command.return_value = {'result': {'node': {'nodeId': 1}}}
    
    # Corrected instantiation: connection_handler is the second argument
    el = WebElement(object_id='1', connection_handler=handler)
    
    # 1. Test _describe_node error path (Line 696)
    handler.execute_command.return_value = {'error': 'Node not found'}
    result = await el._describe_node('some-id')
    assert result == {}
    
    # 2. Test _resolve_routing with IFrameContext (Line 723)
    iframe_handler = AsyncMock()
    iframe_handler.execute_command.return_value = {'result': {'value': 'ok'}}
    
    ctx = IFrameContext(
        frame_id='frame-1',
        session_id='session-1',
        session_handler=iframe_handler
    )
    el._iframe_context = ctx
    
    # This should hit line 723 in _resolve_routing
    h, sid = el._resolve_routing()
    assert h == iframe_handler
    assert sid == 'session-1'
    
    # 3. Test _execute_command with sessionId (Line 735)
    cmd = {'method': 'Runtime.evaluate', 'params': {'expression': '1+1'}}
    await el._execute_command(cmd)
    
    assert iframe_handler.execute_command.called
    assert cmd['sessionId'] == 'session-1' # Hits line 735
    
    # 4. Test fallback routing path (Line 726)
    el._iframe_context = None
    el._routing_session_handler = handler
    el._routing_session_id = 'routing-session-1'
    
    # This should hit line 726 in _resolve_routing
    h, sid = el._resolve_routing()
    assert h == handler
    assert sid == 'routing-session-1'
    
    # Verify execution hits the handler with correct sessionId
    cmd2 = {'method': 'Foo.bar', 'params': {}}
    await el._execute_command(cmd2)
    assert cmd2['sessionId'] == 'routing-session-1'
