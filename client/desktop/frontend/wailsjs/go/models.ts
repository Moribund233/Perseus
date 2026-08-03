export namespace main {
	
	export class GatewayConfig {
	    baseURL: string;
	    gatewayToken: string;
	
	    static createFrom(source: any = {}) {
	        return new GatewayConfig(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.baseURL = source["baseURL"];
	        this.gatewayToken = source["gatewayToken"];
	    }
	}

}

