declare global {
  interface Window {
    go?: {
      main: {
        App: {
          GetGatewayConfig: () => Promise<{ baseURL: string; gatewayToken: string }>;
          OpenFolderDialog: () => Promise<string>;
          OpenFileDialog: () => Promise<string>;
          SaveFileDialog: (defaultName: string) => Promise<string>;
          KeychainGet: (service: string, account: string) => Promise<string>;
          KeychainSet: (service: string, account: string, secret: string) => Promise<void>;
          KeychainDelete: (service: string, account: string) => Promise<void>;
        };
      };
    };
  }
}

export {};
