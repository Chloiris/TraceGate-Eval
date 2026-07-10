import { TraceGateApiError } from "@tracegate/api-client";
import { HostBridgeError } from "../host/hostBridge";

export function errorMessage(error: unknown): string {
  if (error instanceof TraceGateApiError || error instanceof HostBridgeError) {
    return error.message;
  }
  if (error instanceof Error && error.message.trim() !== "") {
    return error.message;
  }
  return "发生未知错误。请查看后端日志并重试。";
}
