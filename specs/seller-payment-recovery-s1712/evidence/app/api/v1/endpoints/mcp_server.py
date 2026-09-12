"""
MCP (Model Context Protocol) Server SSE Endpoint
===============================================

PURPOSE:
    MCP Server implementation with Server-Sent Events for real-time tool discovery.
    Provides MCP handshake and tool manifest via SSE stream.

ARCHITECTURE:
    MCP Client → GET /api/v1/mcp/sse → SSE Stream → Tool Manifest
    
AUTHENTICATION:
    - X-Agent-Key header for internal agents (service bus callers)
    - Future: OAuth Bearer tokens for external agents

PHASE: P1.1 - MCP Server SSE Endpoint  
CREATED: January 31, 2026
"""

from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.responses import StreamingResponse
from typing import Dict, Any, List, AsyncGenerator
from datetime import datetime
import json
import asyncio
import logging

from app.api.deps import get_current_agent
from app.schemas.agent_auth import AgentIdentity, AgentTrustLevel

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# MCP Tool Manifest
# =============================================================================

def get_mcp_tool_manifest() -> List[Dict[str, Any]]:
    """
    Return the ai.market tool manifest for MCP clients.
    
    Defines the 5 core tools available for MCP consumption:
    - search_datasets: Find datasets in the marketplace
    - get_schema: Get dataset schema information  
    - check_price: Check pricing for a dataset
    - get_synthetic_preview: Get synthetic data preview
    - buy_instant: Purchase dataset instantly
    """
    return [
        {
            "name": "search_datasets",
            "description": "Search for datasets in the ai.market marketplace",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for datasets"
                    },
                    "category": {
                        "type": "string",
                        "description": "Dataset category filter",
                        "enum": ["computer_vision", "nlp", "audio", "tabular", "time_series", "other"]
                    },
                    "price_range": {
                        "type": "object",
                        "properties": {
                            "min": {"type": "number", "description": "Minimum price"},
                            "max": {"type": "number", "description": "Maximum price"}
                        },
                        "description": "Price range filter"
                    },
                    "limit": {
                        "type": "integer", 
                        "default": 10,
                        "description": "Maximum number of results"
                    }
                },
                "required": ["query"]
            }
        },
        {
            "name": "get_schema",
            "description": "Get detailed schema information for a dataset",
            "inputSchema": {
                "type": "object", 
                "properties": {
                    "dataset_id": {
                        "type": "string",
                        "description": "Dataset identifier"
                    },
                    "include_samples": {
                        "type": "boolean",
                        "default": False,
                        "description": "Include sample data in response"
                    }
                },
                "required": ["dataset_id"]
            }
        },
        {
            "name": "check_price",
            "description": "Check current pricing for a dataset", 
            "inputSchema": {
                "type": "object",
                "properties": {
                    "dataset_id": {
                        "type": "string",
                        "description": "Dataset identifier"
                    },
                    "usage_type": {
                        "type": "string", 
                        "enum": ["commercial", "research", "personal"],
                        "default": "commercial",
                        "description": "Intended usage type"
                    }
                },
                "required": ["dataset_id"]
            }
        },
        {
            "name": "get_synthetic_preview",
            "description": "Get synthetic preview of dataset for evaluation",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "dataset_id": {
                        "type": "string",
                        "description": "Dataset identifier"
                    },
                    "sample_size": {
                        "type": "integer",
                        "default": 100,
                        "description": "Number of synthetic samples to generate"
                    },
                    "format": {
                        "type": "string",
                        "enum": ["json", "csv", "parquet"],
                        "default": "json", 
                        "description": "Output format for preview data"
                    }
                },
                "required": ["dataset_id"]
            }
        },
        {
            "name": "buy_instant",
            "description": "Purchase a dataset instantly with stored payment method",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "dataset_id": {
                        "type": "string",
                        "description": "Dataset identifier"
                    },
                    "license_type": {
                        "type": "string",
                        "enum": ["single_use", "unlimited", "enterprise"],
                        "default": "single_use",
                        "description": "License type for purchase"
                    },
                    "usage_description": {
                        "type": "string",
                        "description": "Description of intended usage (required for compliance)"
                    }
                },
                "required": ["dataset_id", "usage_description"]
            }
        }
    ]


# =============================================================================
# SSE Event Generation
# =============================================================================

async def generate_mcp_sse_events(agent: AgentIdentity, request: Request) -> AsyncGenerator[str, None]:
    """
    Generate Server-Sent Events for MCP handshake and tool manifest.
    
    MCP SSE Protocol:
    1. Connection established
    2. Server capabilities announcement  
    3. Tool manifest delivery
    4. Keep-alive heartbeat
    """
    try:
        # SSE connection established
        yield f"event: connected\n"
        yield f"data: {json.dumps({'type': 'connected', 'timestamp': datetime.utcnow().isoformat(), 'agent_id': agent.id})}\n\n"
        
        await asyncio.sleep(0.1)  # Brief pause for client processing
        
        # MCP server capabilities
        capabilities = {
            "type": "capabilities",
            "server": {
                "name": "ai.market MCP Server",
                "version": "1.0.0",
                "protocolVersion": "1.0.0"
            },
            "capabilities": {
                "tools": {
                    "listChanged": False  # Static tool list for now
                },
                "logging": {},
                "prompts": {},
                "resources": {}
            },
            "serverInfo": {
                "name": "ai.market",
                "version": "1.0.0"
            }
        }
        
        yield f"event: capabilities\n"
        yield f"data: {json.dumps(capabilities)}\n\n"
        
        await asyncio.sleep(0.1)
        
        # Tool manifest
        tools = get_mcp_tool_manifest()
        
        # Send tools in chunks for better streaming experience
        for i, tool in enumerate(tools):
            tool_event = {
                "type": "tool", 
                "tool": tool,
                "index": i,
                "total": len(tools)
            }
            
            yield f"event: tool\n"
            yield f"data: {json.dumps(tool_event)}\n\n"
            
            await asyncio.sleep(0.05)  # Small delay between tools
        
        # Tool manifest complete
        manifest_complete = {
            "type": "tools_complete",
            "count": len(tools),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        yield f"event: tools_complete\n"
        yield f"data: {json.dumps(manifest_complete)}\n\n"
        
        # Keep-alive heartbeat loop
        heartbeat_count = 0
        while True:
            # Check if client disconnected
            if await request.is_disconnected():
                logger.info(f"MCP SSE client disconnected: agent {agent.id}")
                break
                
            # Send heartbeat every 30 seconds
            await asyncio.sleep(30)
            heartbeat_count += 1
            
            heartbeat = {
                "type": "heartbeat",
                "count": heartbeat_count,
                "timestamp": datetime.utcnow().isoformat(),
                "server_status": "healthy"
            }
            
            yield f"event: heartbeat\n"
            yield f"data: {json.dumps(heartbeat)}\n\n"
            
            logger.debug(f"MCP SSE heartbeat sent: agent {agent.id}, count {heartbeat_count}")
            
    except asyncio.CancelledError:
        logger.info(f"MCP SSE stream cancelled for agent {agent.id}")
        raise
    except Exception as e:
        logger.error(f"MCP SSE stream error for agent {agent.id}: {str(e)}")
        
        error_event = {
            "type": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        yield f"event: error\n"
        yield f"data: {json.dumps(error_event)}\n\n"


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/sse")
async def mcp_sse_endpoint(
    request: Request,
    agent: AgentIdentity = Depends(get_current_agent),
) -> StreamingResponse:
    """
    MCP Server-Sent Events endpoint for real-time tool discovery.
    
    Implements MCP handshake protocol via SSE stream:
    1. Connection establishment
    2. Server capabilities announcement
    3. Tool manifest streaming  
    4. Keep-alive heartbeat
    
    ## Authentication
    
    Requires X-Agent-Key header with valid agent credentials.
    
    ## SSE Event Types
    
    - **connected**: Initial connection confirmation
    - **capabilities**: Server capabilities and protocol version
    - **tool**: Individual tool definition (streamed)
    - **tools_complete**: All tools sent confirmation
    - **heartbeat**: Keep-alive signal (every 30s)
    - **error**: Error notification
    
    ## Usage Example
    
    ```javascript
    const eventSource = new EventSource('/api/v1/mcp/sse', {
        headers: {
            'X-Agent-Key': 'your-agent-key'
        }
    });
    
    eventSource.addEventListener('tool', (event) => {
        const toolData = JSON.parse(event.data);
        console.log('Received tool:', toolData.tool.name);
    });
    
    eventSource.addEventListener('tools_complete', (event) => {
        console.log('All tools received');
    });
    ```
    
    ## Tool Manifest
    
    Provides 5 core ai.market tools:
    - **search_datasets**: Find datasets in marketplace
    - **get_schema**: Get dataset schema information
    - **check_price**: Check dataset pricing
    - **get_synthetic_preview**: Get synthetic preview data
    - **buy_instant**: Purchase dataset instantly
    
    ## Error Handling
    
    - Stream automatically reconnects on network issues
    - Invalid agent credentials return 401 Unauthorized
    - Server errors sent as SSE error events
    """
    logger.info(f"MCP SSE connection started for agent {agent.id} ({agent.name})")
    
    # Validate agent permissions - allow both internal and external agents
    # External agents can also use MCP server for tool discovery
    if agent.trust_level not in [AgentTrustLevel.INTERNAL, AgentTrustLevel.EXTERNAL]:
        logger.warning(f"MCP SSE access denied for agent {agent.id}: invalid trust level {agent.trust_level}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Agent trust level invalid for MCP server access"
        )
    
    return StreamingResponse(
        generate_mcp_sse_events(agent, request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Credentials": "true",
        }
    )


@router.get("/tools/manifest")
async def mcp_tools_manifest(
    agent: AgentIdentity = Depends(get_current_agent),
) -> Dict[str, Any]:
    """
    Get static tool manifest for MCP clients that prefer HTTP over SSE.
    
    Returns the same tool manifest as the SSE endpoint but as a single HTTP response.
    Useful for clients that don't support Server-Sent Events.
    
    ## Response Format
    
    ```json
    {
        "tools": [
            {
                "name": "search_datasets",
                "description": "Search for datasets...",
                "inputSchema": {...}
            }
        ],
        "server": {
            "name": "ai.market MCP Server",
            "version": "1.0.0"
        },
        "count": 5
    }
    ```
    """
    logger.info(f"MCP tools manifest requested by agent {agent.id}")
    
    tools = get_mcp_tool_manifest()
    
    return {
        "tools": tools,
        "server": {
            "name": "ai.market MCP Server",
            "version": "1.0.0",
            "protocolVersion": "1.0.0"
        },
        "count": len(tools),
        "timestamp": datetime.utcnow().isoformat(),
        "agent_context": {
            "id": agent.id,
            "name": agent.name,
            "trust_level": agent.trust_level.value
        }
    }


@router.get("/status")
async def mcp_server_status() -> Dict[str, Any]:
    """
    MCP server status endpoint for health monitoring.
    
    Returns server health and configuration information.
    """
    return {
        "status": "healthy",
        "server": "ai.market MCP Server",
        "version": "1.0.0", 
        "protocol_version": "1.0.0",
        "capabilities": {
            "sse": True,
            "tools": True,
            "manifest": True
        },
        "endpoints": {
            "sse": "/api/v1/mcp/sse",
            "manifest": "/api/v1/mcp/tools/manifest", 
            "status": "/api/v1/mcp/status"
        },
        "timestamp": datetime.utcnow().isoformat()
    }
