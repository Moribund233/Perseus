package gateway

import (
	"container/list"
	"sync"
	"time"
)

type cachedResponse struct {
	Status  int
	Body    []byte
	Content string // Content-Type
	ts      time.Time
}

// proxyCache 只读 GET 响应的内存 LRU 缓存。
// 上限：条目数 capEntries、总字节 capBytes；TTL 后失效逐出。
type proxyCache struct {
	mu         sync.Mutex
	capEntries int
	capBytes   int
	ttl        time.Duration
	ll         *list.List
	items      map[string]*list.Element
	bytes      int
}

type cacheItem struct {
	key  string
	data cachedResponse
}

func newProxyCache(capEntries, capBytes int, ttl time.Duration) *proxyCache {
	return &proxyCache{
		capEntries: capEntries,
		capBytes:   capBytes,
		ttl:        ttl,
		ll:         list.New(),
		items:      map[string]*list.Element{},
	}
}

func (c *proxyCache) get(key string) (cachedResponse, bool) {
	c.mu.Lock()
	defer c.mu.Unlock()
	el, ok := c.items[key]
	if !ok {
		return cachedResponse{}, false
	}
	item := el.Value.(*cacheItem)
	if time.Since(item.data.ts) > c.ttl {
		c.remove(el)
		return cachedResponse{}, false
	}
	c.ll.MoveToFront(el)
	return item.data, true
}

func (c *proxyCache) put(key string, data cachedResponse) {
	c.mu.Lock()
	defer c.mu.Unlock()
	data.ts = time.Now()
	if el, ok := c.items[key]; ok {
		c.ll.MoveToFront(el)
		el.Value.(*cacheItem).data = data
		return
	}
	el := c.ll.PushFront(&cacheItem{key: key, data: data})
	c.items[key] = el
	c.bytes += len(data.Body)
	c.evict()
}

func (c *proxyCache) remove(el *list.Element) {
	item := el.Value.(*cacheItem)
	delete(c.items, item.key)
	c.bytes -= len(item.data.Body)
	c.ll.Remove(el)
}

func (c *proxyCache) evict() {
	for c.ll.Len() > c.capEntries || c.bytes > c.capBytes {
		back := c.ll.Back()
		if back == nil {
			return
		}
		c.remove(back)
	}
}