// hanlaw-skill 빌더 — 클라이언트 사이드 ZIP 생성
// 사용자의 API 키를 템플릿 파일에 주입해 Claude Skill ZIP을 만든다.
// 모든 처리는 브라우저 안에서만 이뤄지며 외부 서버 통신 없음.

(function () {
  "use strict";

  const PLACEHOLDER = "__LAW_API_KEY__";
  const SKILL_NAME = "hanlaw-skill";

  const els = {
    input: document.getElementById("api-key"),
    btn: document.getElementById("build-btn"),
    status: document.getElementById("build-status"),
  };

  function setStatus(msg, type) {
    els.status.textContent = msg;
    els.status.className = "status" + (type ? " " + type : "");
  }

  function validateKey(key) {
    if (!key) return "API 키를 입력해주세요.";
    if (key.length < 6) return "API 키가 너무 짧습니다. 다시 확인해주세요.";
    if (/[\s"']/.test(key)) return "공백이나 따옴표는 키에 포함될 수 없습니다.";
    if (key === PLACEHOLDER)
      return "플레이스홀더 값은 사용할 수 없습니다. 실제 발급키를 입력하세요.";
    return null;
  }

  async function fetchText(path) {
    const res = await fetch(path, { cache: "no-store" });
    if (!res.ok) throw new Error(`${path} 로딩 실패 (HTTP ${res.status})`);
    return res.text();
  }

  async function build() {
    const key = els.input.value.trim();
    const err = validateKey(key);
    if (err) {
      setStatus(err, "err");
      return;
    }

    els.btn.disabled = true;
    setStatus("템플릿 파일 로딩 중…", "");

    try {
      const [skillMd, apiPyTpl, kwJson, devlog] = await Promise.all([
        fetchText("templates/SKILL.md"),
        fetchText("templates/lexguard_api.py.tpl"),
        fetchText("templates/domain_keywords.json"),
        fetchText("templates/DEVLOG.md"),
      ]);

      setStatus("API 키 주입 및 ZIP 생성 중…", "");

      const apiPy = apiPyTpl.split(PLACEHOLDER).join(key);

      if (apiPy.indexOf(PLACEHOLDER) !== -1) {
        throw new Error("치환 후에도 플레이스홀더가 남아있습니다.");
      }

      const zip = new JSZip();
      const root = zip.folder(SKILL_NAME);
      root.file("SKILL.md", skillMd);
      root.file("DEVLOG.md", devlog);
      root.folder("scripts").file("lexguard_api.py", apiPy);
      root.folder("resources").file("domain_keywords.json", kwJson);

      const blob = await zip.generateAsync({
        type: "blob",
        compression: "DEFLATE",
        compressionOptions: { level: 6 },
      });

      const filename = `${SKILL_NAME}.zip`;
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(() => URL.revokeObjectURL(url), 1000);

      setStatus(
        `✅ ${filename} 다운로드 시작됨. 압축 풀어서 Claude skills 폴더에 배치하세요.`,
        "ok"
      );
    } catch (e) {
      console.error(e);
      setStatus(`❌ 오류: ${e.message}`, "err");
    } finally {
      els.btn.disabled = false;
    }
  }

  els.btn.addEventListener("click", build);
  els.input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") build();
  });
})();
