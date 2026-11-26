(function (globalScope) {
    class SseEventParser {
        constructor() {
            this.buffer = '';
        }

        push(text) {
            this.buffer += text;
            const events = [];

            while (true) {
                const boundary = /\r?\n\r?\n/.exec(this.buffer);
                if (!boundary) break;

                const block = this.buffer.slice(0, boundary.index);
                this.buffer = this.buffer.slice(boundary.index + boundary[0].length);
                const dataLines = block
                    .split(/\r?\n/)
                    .filter(line => line.startsWith('data:'))
                    .map(line => line.slice(5).replace(/^ /, ''));
                if (dataLines.length > 0) {
                    events.push(dataLines.join('\n'));
                }
            }

            return events;
        }

        finish(text = '') {
            const events = this.push(text);
            if (this.buffer.trim()) {
                throw new Error('AI 流式响应不完整');
            }
            return events;
        }
    }

    function parseSseJsonEvent(data) {
        if (data === '[DONE]') {
            return { type: 'done' };
        }

        let payload;
        try {
            payload = JSON.parse(data);
        } catch (_error) {
            throw new Error('AI 流式响应格式错误');
        }

        if (payload.error) {
            throw new Error(payload.error);
        }
        if (payload.status) {
            return { type: 'status', status: payload.status };
        }
        if (payload.result && typeof payload.result === 'object') {
            return { type: 'result', result: payload.result };
        }
        if (typeof payload.content === 'string' && payload.content) {
            return { type: 'content', content: payload.content };
        }
        return { type: 'ignore' };
    }

    const api = { SseEventParser, parseSseJsonEvent };
    globalScope.SseStream = api;
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = api;
    }
})(typeof globalThis !== 'undefined' ? globalThis : window);
