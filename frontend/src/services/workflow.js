import axios from "../axiosConfig";

export async function getWorkflowDefinitions() {
  const response = await axios.get(
    "/api/workflow/definitions/"
  );

  return response.data;
}

export async function getWorkflowDefinition(
  workflowId
) {
  const response = await axios.get(
    `/api/workflow/definitions/${workflowId}/`
  );

  return response.data;
}

export async function getWorkflowGraph(
  workflowId
) {
  const response = await axios.get(
    "/api/workflow/builder/graph/",
    {
      params: {
        workflow: workflowId,
      },
    }
  );

  return response.data;
}

export async function publishWorkflow(
  workflowId
) {
  const response = await axios.post(
    `/api/workflow/definitions/${workflowId}/publish/`
  );

  return response.data;
}

export async function getWorkflowRuntime(
  instanceId
) {
  const response = await axios.get(
    `/api/workflow/runtime/${instanceId}/`
  );

  return response.data;
}

export async function executeWorkflowRuntime(
  instanceId,
  action
) {
  const response = await axios.post(
    `/api/workflow/runtime/${instanceId}/`,
    {
      action,
    }
  );

  return response.data;
}

export async function getWorkflowExecutionHistory(
  instanceId
) {
  const response = await axios.get(
    `/api/workflow/runtime/${instanceId}/history/`
  );

  return response.data;
}

export async function createWorkflowRuntime(
  workflowId,
  context = {}
) {
  const response = await axios.post(
    `/api/workflow/definitions/${workflowId}/runtime/`,
    {
      context,
    }
  );

  return response.data;
}