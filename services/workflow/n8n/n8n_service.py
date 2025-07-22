import os
import httpx
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from services.common.log_creator import create_logger
from services.workflow.n8n.models import (
    WorkflowTemplateInfo, 
    WorkflowTemplatesResponse,
    WorkflowExecuteResponse,
    N8nWorkflowCloneRequest,
    N8nWorkflowUpdateRequest
)

# Load environment variables
load_dotenv(override=True)


class N8nService:
    """Service for managing n8n workflow operations"""
    
    def __init__(self):
        # N8N Configuration
        self.n8n_base_url = os.getenv("N8N_BASE_URL", "http://localhost:5678")
        self.n8n_api_key = os.getenv("N8N_API_KEY", "")
        self.env_prefix = os.getenv("N8N_ENV_PREFIX", "v1")
        
        # Logging Configuration
        is_production = os.getenv("IS_PRODUCTION", "no")
        log_url = os.getenv("LOG_URL", ".")
        self.logger = create_logger(is_production, log_url)
        
        if not self.n8n_api_key:
            self.logger.warning("N8N_API_KEY not set - some operations may fail")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for n8n API requests"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        if self.n8n_api_key:
            headers["X-N8N-API-KEY"] = self.n8n_api_key
            
        return headers
    
    def _get_workflow_trigger_url(self, workspace: str, segment: str) -> str:
        """Generate the workflow trigger URL"""
        return f"/{self.env_prefix}/{workspace}/{segment}"
    
    async def execute_workflow(self, workspace: str, segment: str, data: Dict[str, Any]) -> WorkflowExecuteResponse:
        """
        Execute a workflow for the given workspace and segment.
        If workflow doesn't exist (404), attempt to create it from template.
        """
        self.logger.info(f"Executing workflow for workspace: {workspace}, segment: {segment}")
        
        # First, try to execute the existing workflow
        trigger_url = self._get_workflow_trigger_url(workspace, segment)
        workflow_url = f"{self.n8n_base_url}/webhook{trigger_url}"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                workflow_url,
                json=data,
                headers=self._get_headers(),
                timeout=30.0
            )
            
            if response.status_code == 200:
                self.logger.info(f"Workflow executed successfully for {workspace}/{segment}")
                return WorkflowExecuteResponse(
                    success=True,
                    message="Workflow executed successfully",
                )
            elif response.status_code == 404:
                self.logger.info(f"Workflow not found for {workspace}/{segment}, attempting to create from template")
                # Workflow doesn't exist, try to create it from template
                return await self._create_workflow_from_template(workspace, segment, data)
            else:
                raise Exception(
                    f"Workflow execution failed with status {response.status_code}: {response.text}")
                    
    
    async def _create_workflow_from_template(self, workspace: str, segment: str, data: Dict[str, Any]) -> WorkflowExecuteResponse:
        """Create a new workflow from template and execute it"""
            # Find template workflow by tags
        template_workflow = await self._find_template_workflow(segment)
        if not template_workflow:
            raise Exception(
                f"No template workflow found for segment '{segment}'"
                 )
        # Clone the template workflow
        new_workflow_name = f"{workspace}_{segment}"
        cloned_workflow = await self._clone_workflow(template_workflow['id'], new_workflow_name, workspace, segment)
        
        if not cloned_workflow:
            raise Exception(
                f"Failed to clone template workflow for workspace '{workspace}' and segment '{segment}'"
                )
        
        
        # Activate the workflow
        await self._activate_workflow_api(cloned_workflow['id'])
        
        # Now try to execute the workflow
        self.logger.info(f"Created workflow '{new_workflow_name}', attempting execution")
        return await self.execute_workflow(workspace, segment, data)
        
    
    async def _find_template_workflow(self, segment: str) -> Optional[Dict[str, Any]]:
        """Find a template workflow that matches the workspace and segment tags"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.n8n_base_url}/api/v1/workflows?tags=template",
                headers=self._get_headers(),
                timeout=30.0
            )
            
            if response.status_code != 200:
                self.logger.error(f"Failed to fetch workflows: {response.status_code}")
                return None
            
            workflows = response.json().get('data', [])
            
            # Find workflows with 'template' tag and matching workspace/segment
            for workflow in workflows:
                tags = workflow.get('tags', [])
                if isinstance(tags, list):
                    tag_names = [tag.get('name', '') if isinstance(tag, dict) else str(tag) for tag in tags]
                else:
                    tag_names = []
                
                # Check if this workflow has template tag and matches workspace and segment
                if ('template' in tag_names and
                    segment in tag_names):
                    
                    self.logger.info(f"Found template workflow: {workflow.get('name')} with tags: {tag_names}")
                    return workflow
            
            self.logger.warning(f"No template workflow found with tags: template, {segment}")
            return None
                
    
    async def _clone_workflow(self, workflow_id: str, new_name: str, workspace: str, segment: str) -> Optional[Dict[str, Any]]:
        """Clone a workflow with a new name"""
            # First get the source workflow
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.n8n_base_url}/api/v1/workflows/{workflow_id}",
                headers=self._get_headers(),
                timeout=30.0
            )
            
            if response.status_code != 200:
                self.logger.error(f"Failed to fetch source workflow: {response.status_code}")
                return None
            
            source_workflow = response.json()
            del source_workflow['id']
            # Create new workflow with cloned data
            clone_data = {
                "name": new_name,
                "nodes": source_workflow.get('nodes', []),
                "connections": source_workflow.get('connections', {}),
                "settings": source_workflow.get('settings', {})
            }

            # Find the node
            llm_trigger_node = [data for data in clone_data["nodes"] if data['name'] == 'llm trigger'][0]
            # Set the 'path' parameter to a new value
            llm_trigger_node["parameters"]["path"] = f"{self.env_prefix}/{workspace}/{segment}"

            
            # Create the new workflow
            create_response = await client.post(
                f"{self.n8n_base_url}/api/v1/workflows",
                json=clone_data,
                headers=self._get_headers(),
                timeout=30.0
            )
            
            if create_response.status_code == 200:
                cloned_workflow = create_response.json()
                self.logger.info(f"Successfully cloned workflow: {new_name}")
                return cloned_workflow
            else:
                self.logger.error(f"Failed to create cloned workflow: {create_response.status_code}")
                return None
                
    
    async def _update_workflow_trigger(self, workflow_id: str, new_trigger_url: str) -> Optional[Dict[str, Any]]:
        """Update the webhook trigger URL in a workflow"""
        async with httpx.AsyncClient() as client:
            # Get current workflow
            response = await client.get(
                f"{self.n8n_base_url}/api/v1/workflows/{workflow_id}",
                headers=self._get_headers(),
                timeout=30.0
            )
            
            if response.status_code != 200:
                return None
            
            workflow = response.json().get('data', {})
            nodes = workflow.get('nodes', [])
            
            # Find and update webhook trigger nodes
            for node in nodes:
                if node.get('type') == 'n8n-nodes-base.webhook':
                    if 'parameters' not in node:
                        node['parameters'] = {}
                    node['parameters']['path'] = new_trigger_url
                    self.logger.info(f"Updated webhook trigger path to: {new_trigger_url}")
            
            # Update the workflow
            update_data = {
                "nodes": nodes,
                "connections": workflow.get('connections', {}),
                "settings": workflow.get('settings', {})
            }
            
            update_response = await client.put(
                f"{self.n8n_base_url}/api/v1/workflows/{workflow_id}",
                json=update_data,
                headers=self._get_headers(),
                timeout=30.0
            )
            
            if update_response.status_code == 200:
                self.logger.info(f"Successfully updated workflow trigger for workflow: {workflow_id}")
                return update_response.json().get('data', {})
            else:
                self.logger.error(f"Failed to update workflow: {update_response.status_code}")
                return None

    
    async def _activate_workflow_api(self, workflow_id: str) -> bool:
        """Activate a workflow via n8n API"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.n8n_base_url}/api/v1/workflows/{workflow_id}/activate",
                headers=self._get_headers(),
                timeout=30.0
            )
            
            if response.status_code == 200:
                self.logger.info(f"Successfully activated workflow: {workflow_id}")
                return True
            else:
                self.logger.error(f"Failed to activate workflow: {response.status_code}")
                return False
                    
    
    async def get_template_workflows(self) -> WorkflowTemplatesResponse:
        """Get all workflows with 'template' tag"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.n8n_base_url}/api/v1/workflows?tags=template",
                headers=self._get_headers(),
                timeout=30.0
            )
            
            if response.status_code != 200:
                error_msg = f"Failed to fetch workflows: {response.status_code}"
                self.logger.error(error_msg)
                return WorkflowTemplatesResponse(
                    success=False,
                    templates=[],
                    message=error_msg,
                )
            
            workflows = response.json().get('data', [])
            templates = []
            
            for workflow in workflows:
                tags = workflow.get('tags', [])
                if isinstance(tags, list):
                    tag_names = [tag.get('name', '') if isinstance(tag, dict) else str(tag) for tag in tags]
                else:
                    tag_names = []
                
                # Check if this workflow has 'template' tag
                if 'template' in tag_names:
                    # Extract workspace from tags (assuming it's not 'template' or common segment names)
                    workspace = None
                    for tag in tag_names:
                        if tag not in ['template']:  # Add other common tags to exclude if needed
                            workspace = tag
                            break
                    
                    template_info = WorkflowTemplateInfo(
                        id=workflow.get('id', ''),
                        name=workflow.get('name', ''),
                        description=workflow.get('description', ''),  # n8n doesn't have separate description field
                        workspace=workspace,
                        tags=tag_names
                    )
                    templates.append(template_info)
            
            self.logger.info(f"Found {len(templates)} template workflows")
            return WorkflowTemplatesResponse(
                success=True,
                templates=templates,
                message=f"Found {len(templates)} template workflows"
            )
                



# Create service instance
n8n_service = N8nService() 