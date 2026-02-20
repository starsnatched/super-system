import SwiftUI
import WebKit

struct PreviewPanel: View {
    @Binding var urlString: String
    @State private var editingURL: String = ""
    @State private var webViewId = UUID()

    var body: some View {
        VStack(spacing: 0) {
            addressBar
            WebViewWrapper(urlString: urlString)
                .id(webViewId)
        }
        .onAppear {
            editingURL = urlString
        }
        .onChange(of: urlString) { _, newValue in
            editingURL = newValue
        }
    }

    private var addressBar: some View {
        HStack(spacing: 6) {
            Button("Reload", systemImage: "arrow.clockwise") {
                webViewId = UUID()
            }
            .labelStyle(.iconOnly)
            .buttonStyle(.borderless)
            .font(.system(size: 11))
            .foregroundStyle(.tertiary)
            .help("Reload")

            HStack(spacing: 5) {
                Image(systemName: "globe")
                    .font(.system(size: 9))
                    .foregroundStyle(.quaternary)

                TextField("URL", text: $editingURL)
                    .textFieldStyle(.plain)
                    .font(.caption.monospaced())
                    .onSubmit {
                        urlString = normalizeURL(editingURL)
                    }
            }
            .padding(.horizontal, 8)
            .padding(.vertical, 5)
            .glassEffect(in: .capsule)

            Button("Open in Browser", systemImage: "arrow.up.right.square") {
                if let url = URL(string: normalizeURL(urlString)) {
                    NSWorkspace.shared.open(url)
                }
            }
            .labelStyle(.iconOnly)
            .buttonStyle(.borderless)
            .font(.system(size: 11))
            .foregroundStyle(.tertiary)
            .help("Open in browser")
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 6)
        .background(.bar)
    }

    private func normalizeURL(_ input: String) -> String {
        let trimmed = input.trimmingCharacters(in: .whitespacesAndNewlines)
        if trimmed.hasPrefix("http://") || trimmed.hasPrefix("https://") {
            return trimmed
        }
        return "http://\(trimmed)"
    }
}

struct WebViewWrapper: NSViewRepresentable {
    let urlString: String

    func makeNSView(context: Context) -> WKWebView {
        let config = WKWebViewConfiguration()
        config.preferences.setValue(true, forKey: "developerExtrasEnabled")
        let webView = WKWebView(frame: .zero, configuration: config)
        webView.allowsMagnification = true
        if let url = URL(string: urlString) {
            webView.load(URLRequest(url: url))
        }
        return webView
    }

    func updateNSView(_ webView: WKWebView, context: Context) {
        guard let url = URL(string: urlString) else { return }
        if webView.url?.absoluteString != url.absoluteString {
            webView.load(URLRequest(url: url))
        }
    }
}
