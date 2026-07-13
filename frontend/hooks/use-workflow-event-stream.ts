"use client";

import { useCallback, useEffect, useState } from "react";

import {
  buildWorkflowEventStreamUrl,
  parseWorkflowEventStreamMessage,
} from "@/lib/streaming/workflow-events";
import type { WorkflowEventStreamMessage } from "@/lib/api/types";

export type WorkflowStreamConnectionStatus =
  | "connecting"
  | "connected"
  | "disconnected"
  | "error";

interface WorkflowEventStreamState {
  status: WorkflowStreamConnectionStatus;
  messages: WorkflowEventStreamMessage[];
  errorMessage: string | null;
  reconnect: () => void;
}

interface UseWorkflowEventStreamOptions {
  workflowId: string;
  accessToken: string | null;
}

export function useWorkflowEventStream({
  workflowId,
  accessToken,
}: UseWorkflowEventStreamOptions): WorkflowEventStreamState {
  const [status, setStatus] =
    useState<WorkflowStreamConnectionStatus>("disconnected");
  const [messages, setMessages] = useState<WorkflowEventStreamMessage[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [connectionAttempt, setConnectionAttempt] = useState(0);

  const reconnect = useCallback(() => {
    setConnectionAttempt((attempt) => attempt + 1);
  }, []);

  useEffect(() => {
    if (!accessToken) {
      setStatus("disconnected");
      setErrorMessage("Sign in to open the workflow event stream.");
      return;
    }
    if (typeof WebSocket === "undefined") {
      setStatus("error");
      setErrorMessage("WebSocket is not available in this browser.");
      return;
    }

    const socket = new WebSocket(
      buildWorkflowEventStreamUrl(workflowId, accessToken),
    );
    let closedByCleanup = false;

    setStatus("connecting");
    setErrorMessage(null);

    socket.onopen = () => {
      setStatus("connected");
      setErrorMessage(null);
    };

    socket.onmessage = (event) => {
      const message = parseWorkflowEventStreamMessage(String(event.data));
      if (message === null) {
        setStatus("error");
        setErrorMessage("Received an invalid workflow stream message.");
        return;
      }
      setMessages((currentMessages) => [...currentMessages, message]);
    };

    socket.onerror = () => {
      setStatus("error");
      setErrorMessage("Workflow event stream connection failed.");
    };

    socket.onclose = () => {
      if (!closedByCleanup) {
        setStatus("disconnected");
      }
    };

    return () => {
      closedByCleanup = true;
      socket.close();
    };
  }, [accessToken, connectionAttempt, workflowId]);

  return {
    status,
    messages,
    errorMessage,
    reconnect,
  };
}
