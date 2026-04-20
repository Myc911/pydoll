import pytest
from unittest.mock import AsyncMock, MagicMock
from pydoll.elements.web_element import WebElement
from pydoll.interactions.iframe import IFrameContext
from pydoll.exceptions import ElementNotFound
import asyncio

@pytest.mark.asyncio
async def test_find_elements_mixin_routing_coverage():
    handler = AsyncMock()
    handler.execute_command.return_value = {'result': {'node': {'nodeId': 1}}}
    
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
    
    h, sid = el._resolve_routing()
    assert h == handler
    assert sid == 'routing-session-1'
    
    cmd2 = {'method': 'Foo.bar', 'params': {}}
    await el._execute_command(cmd2)
    assert cmd2['sessionId'] == 'routing-session-1'

@pytest.mark.asyncio
async def test_find_across_iframes_timeout_not_raise():
    handler = AsyncMock()
    el = WebElement(object_id='1', connection_handler=handler)
    
    # Mock attempt_find_across_iframes to return None
    el._attempt_find_across_iframes = AsyncMock(return_value=None)
    
    # timeout > 0, raise_exc=False. Should timeout and return [] or None
    # We patch asyncio.sleep to avoid real wait, and time() to advance time fast
    original_time = asyncio.get_event_loop().time
    
    calls = []
    def fake_time():
        calls.append(1)
        return original_time() + len(calls) * 20 # Advance time by 20s each check
        
    async def fake_sleep(t):
        pass
    
    loop = asyncio.get_event_loop()
    loop.time = fake_time
    asyncio.sleep = fake_sleep
    
    try:
        res = await el._find_across_iframes([], timeout=5, find_all=True, raise_exc=False)
        assert res == []
        res_none = await el._find_across_iframes([], timeout=5, find_all=False, raise_exc=False)
        assert res_none is None
    finally:
        loop.time = original_time
        # don't strictly need to restore sleep, test ends

@pytest.mark.asyncio
async def test_find_elements_empty_not_raise():
    handler = AsyncMock()
    el = WebElement(object_id='1', connection_handler=handler)
    
    # Test line 554-557
    handler.execute_command.return_value = {'result': {}}
    
    res = await el._find_elements('id', 'test', raise_exc=False)
    assert res == []

@pytest.mark.asyncio
async def test_find_elements_keyerror_skip():
    handler = AsyncMock()
    el = WebElement(object_id='1', connection_handler=handler)
    
    # Test line 574-575
    # First get_properties returns an object format
    handler.execute_command.side_effect = [
        {'result': {'result': {'objectId': 'array-id'}}}, # eval result
        {'result': {'result': [{'name': '0', 'value': {'objectId': 'child-id'}}]}} # get_properties
    ]
    
    el._describe_node = AsyncMock(side_effect=KeyError('mock error'))
    
    res = await el._find_elements('id', 'test', raise_exc=False)
    assert res == []
