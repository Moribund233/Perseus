package gateway

import "net/http"

type ConfigResponse struct {
	BaseURL         string `json:"baseURL"`
	GatewayToken    string `json:"gatewayToken"`
	DefaultServerID string `json:"defaultServerId"`
}

func (g *Gateway) handleConfig(w http.ResponseWriter, r *http.Request) {
	baseURL := "http://" + g.Addr()
	defaultID, _ := g.store.GetSetting("default_server_id")
	writeJSON(w, http.StatusOK, ConfigResponse{BaseURL: baseURL, GatewayToken: g.token, DefaultServerID: defaultID})
}
