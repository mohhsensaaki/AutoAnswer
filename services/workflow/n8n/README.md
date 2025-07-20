# n8n Workflow Service

This service provides automated workflow management using n8n, allowing dynamic workflow creation and execution based on workspace and segment parameters.

## Features

- **Dynamic Workflow Execution**: Execute workflows based on workspace/segment parameters
- **Automatic Template Cloning**: Create new workflows from templates when they don't exist
- **Template Management**: List and manage workflow templates
- **URL Path Management**: Automatically configure webhook trigger URLs

## API Endpoints

### 1. Execute Workflow
```
POST /api/v1/workflow/{workspace}/{segment}
```

Executes a workflow for the specified workspace and segment. If the workflow doesn't exist, it automatically creates one from a template.

**Parameters:**
- `workspace`: Workspace identifier (URL parameter)
- `segment`: Segment identifier (URL parameter)
- Request body: Any JSON data to pass to the workflow

**Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/workflow/mycompany/support" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "123", "message": "Hello from workflow"}'
```

**Response:**
```json
{
  "status": true,
  "meta": {
    "start_at": "2024-01-01T10:00:00",
    "end_at": "2024-01-01T10:00:01",
    "run_time_duration": 1,
    "exception": null
  },
  "data": {
    "success": true,
    "message": "Workflow executed successfully",
    "workflow_id": "workflow_123",
    "execution_id": "exec_456",
    "data": { /* workflow response data */ }
  }
}
```

### 2. Get Template Workflows
```
GET /api/v1/workflow/templates
```

Returns a list of all workflow templates (workflows with 'template' tag).

**Example:**
```bash
curl "http://localhost:8000/api/v1/workflow/templates"
```

**Response:**
```json
{
  "status": true,
  "meta": { /* meta information */ },
  "data": {
    "success": true,
    "templates": [
      {
        "id": "template_123",
        "name": "Support Template",
        "description": "Support Template",
        "workspace": "mycompany",
        "tags": ["template", "mycompany", "support"]
      }
    ],
    "message": "Found 1 template workflows"
  }
}
```

### 3. Health Check
```
GET /api/v1/workflow/health
```

Returns the health status of the n8n workflow service.

## How It Works

### Workflow Execution Flow

1. **Initial Request**: User makes POST request to `/api/v1/workflow/{workspace}/{segment}`
2. **URL Generation**: Service generates webhook URL: `/{env_prefix}/{workspace}/{segment}`
3. **Workflow Execution**: Attempts to execute existing workflow at the generated URL
4. **Auto-Creation on 404**: If workflow doesn't exist (404 error):
   - Searches for template workflows with tags: `['template', workspace, segment]`
   - Clones the matching template workflow
   - Updates the webhook trigger URL to the generated path
   - Names the new workflow: `{template_name}_{workspace}_{segment}`
   - Activates the workflow
   - Executes the original request

### Template Workflow Requirements

For automatic workflow creation to work, template workflows must:

1. **Have Required Tags**: Include tags for `template`, `workspace`, and `segment`
2. **Contain Webhook Trigger**: Have at least one webhook trigger node
3. **Be Accessible**: Be available through the n8n API

**Example Template Tags:**
- `template` (required)
- `mycompany` (workspace)
- `support` (segment)

## Configuration

### Environment Variables

Create a `.env` file or add to your main project `.env`:

```env
# n8n API Configuration
N8N_API_URL=http://localhost:5678/api/v1
N8N_API_KEY=your_n8n_api_key_here

# Workflow Configuration  
N8N_ENV_PREFIX=v1

# Application Configuration
IS_PRODUCTION=no
LOG_URL=.
```

### n8n Setup

1. **Install n8n**:
   ```bash
   npm install n8n -g
   # or
   docker run -it --rm --name n8n -p 5678:5678 n8nio/n8n
   ```

2. **Enable API Access**:
   - Go to n8n Settings > API
   - Create an API key
   - Add the key to your `.env` file

3. **Create Template Workflows**:
   - Create workflows in n8n with webhook triggers
   - Add appropriate tags: `template`, `workspace`, `segment`
   - Save and activate the template workflows

## Usage Examples

### Basic Workflow Execution

```python
import httpx

async def execute_workflow():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/workflow/mycompany/support",
            json={
                "customer_id": "12345",
                "issue": "Login problem",
                "priority": "high"
            }
        )
        return response.json()
```

### List Templates

```python
async def get_templates():
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://localhost:8000/api/v1/workflow/templates"
        )
        return response.json()
```

## Error Handling

The service handles various error scenarios:

- **Missing Template**: Returns error if no template workflow found for workspace/segment
- **n8n API Errors**: Propagates n8n API errors with detailed messages
- **Network Issues**: Handles connection timeouts and network failures
- **Invalid Data**: Validates request data and returns appropriate errors

## Logging

The service uses the common logging framework and logs:
- Workflow execution attempts
- Template searches and cloning
- URL updates and activations
- Error conditions and debugging information

## Security Considerations

- **API Key Protection**: Store n8n API key securely
- **Network Security**: Ensure n8n instance is properly secured
- **Input Validation**: Service validates all input parameters
- **Access Control**: Consider implementing authentication for the API endpoints

## Troubleshooting

### Common Issues

1. **404 Errors with No Template Creation**:
   - Check if template workflow exists with correct tags
   - Verify n8n API connectivity
   - Check API key permissions

2. **Workflow Creation Fails**:
   - Verify n8n API key has sufficient permissions
   - Check n8n instance is running and accessible
   - Review n8n logs for errors

3. **Trigger URL Not Working**:
   - Ensure workflow is activated after creation
   - Verify webhook trigger node configuration
   - Check URL path matches expected pattern

### Debug Steps

1. Check service health: `GET /api/v1/workflow/health`
2. List available templates: `GET /api/v1/workflow/templates`
3. Review application logs for detailed error information
4. Verify n8n instance status and API connectivity 