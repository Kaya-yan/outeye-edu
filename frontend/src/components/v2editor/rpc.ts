export interface VeEnvelope {
  ve: 1;
  ch: string;
  type: string;
  payload?: Record<string, unknown>;
}

export interface VeRect {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface VeChainNode {
  tag: string;
  component: string;
  selector: string;
}

export interface VeTargetStyles {
  display: string;
  fontSize: string;
  fontWeight: string;
  fontFamily: string;
  color: string;
  background: string;
  textAlign: string;
  lineHeight: string;
  margin: string;
  padding: string;
}

export interface VeTarget {
  tag: string;
  id: string;
  cls: string;
  component: string;
  page: string;
  pageTitle: string;
  selector: string;
  rect: VeRect;
  text: string;
  styles: VeTargetStyles;
  chain: VeChainNode[];
}

export interface VePageInfo {
  n: string;
  title: string;
  component: string;
}

export function createHostBridge(channel: string, onMessage: (type: string, payload: Record<string, unknown>) => void) {
  const handler = (e: MessageEvent) => {
    const d = e.data as VeEnvelope | undefined;
    if (!d || d.ve !== 1 || d.ch !== channel) return;
    onMessage(d.type, d.payload || {});
  };
  window.addEventListener("message", handler);
  return {
    send(target: Window | null, type: string, payload?: Record<string, unknown>) {
      target?.postMessage({ ve: 1, ch: channel, type, payload: payload || {} }, "*");
    },
    dispose() {
      window.removeEventListener("message", handler);
    },
  };
}

export type HostBridge = ReturnType<typeof createHostBridge>;
