import { useCallback, useEffect, useLayoutEffect, useMemo, useState } from "react";
import { List, useDynamicRowHeight, useListRef, type RowComponentProps } from "react-window";
import { useSearchParams } from "react-router-dom";

import "./App.scss";

interface Build {
  attrpath: string;
  hydra_id: number | null;
  tag: string;
  error_line_number: number | null;
  last_success_rev: string | null;
  last_success_date: string | null;
}

interface Commit {
  name: string;
  rev: string;
  date: string;
}

interface ApiResponse {
  builds: Build[];
  commit: Commit;
}

function BuildEntry({
  index,
  builds,
  selected,
  onSelect,
  style
}: RowComponentProps<{
  builds: Build[];
  selected: string | null;
  onSelect: (b: Build) => void }>
) {
  let entry = builds[index];
  let isCurrent = selected === entry.attrpath;

  return (
    <button
      style={style}
      className={"build-entry " + (isCurrent ? "current" : "")}
      onClick={() => onSelect(entry)}
    >
      <span className="attrpath">{entry.attrpath}</span>
    </button>
  );
}

function BuildsTable({ builds, top, selected, onSelect }: {
  builds: Build[];
  top: string | null;
  selected: string | null;
  onSelect: (b: Build) => void;
}) {
  const listRef = useListRef(null);

  useLayoutEffect(() => {
    if (!top) return;

    const idx = builds.findIndex((b) => b.attrpath === top);
    if (idx === -1) return;

    requestAnimationFrame(() => {
      const list = listRef.current;

      list?.scrollToRow({
        align: "start",
        behavior: "smooth",
        index: idx,
      });
    });
  }, []);

  return (
    <List
      listRef={listRef}
      className="build-entries"
      rowComponent={BuildEntry}
      rowCount={builds.length}
      rowHeight={29}
      rowProps={{ builds, selected, onSelect }}
    />
  );
}

function LogLine({
  index,
  logLines,
  errorLineNumber,
  style
}: RowComponentProps<{
  logLines: string[];
  errorLineNumber: number | null;
}>)
{
  const line = logLines[index];
  const isError = index + 1 === errorLineNumber;

  return (
    <div style={style} className={"log-line " + (isError ? 'error' : '')}>
      <span className="lineno" style={{ minWidth: `${logLines.length.toString().length}ch` }}>
        {index + 1}
      </span>
      <span>{line}</span>
    </div>
  );
}

function CopyButton({ textToCopy }: { textToCopy: string }) {
  const [isCopied, setIsCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(textToCopy);
      setIsCopied(true);

      setTimeout(() => {
        setIsCopied(false);
      }, 1000);
    } catch (err) {
      console.error('Failed to copy text: ', err);
    }
  };

  return (
    <button
      onClick={handleCopy}
      className={`btn ${isCopied && "btn-on"}`}
    >
      {isCopied ? 'Copied!' : 'Copy'}
    </button>
  );
}

function LogViewer({
  logContent,
  errorLineNumber,
}: {
  logContent: string;
  errorLineNumber: number | null;
}) {
  const listRef = useListRef(null);
  const logLines = useMemo(() => logContent.split('\n'), [logContent]);

  const jumpToError = useCallback(() => {
    if (!errorLineNumber) return;

    requestAnimationFrame(() => {
      listRef.current?.scrollToRow({
        align: "center",
        behavior: "smooth",
        index: errorLineNumber - 1,
      });
    });
  }, [errorLineNumber]);

  const rowHeight = useDynamicRowHeight({
    defaultRowHeight: 20
  });

  return (
    <>
      <div className="log-actions">
        {errorLineNumber && (
          <button className="btn" onClick={jumpToError}>
            Jump to Error
          </button>
        )}
        <CopyButton textToCopy={logContent} />
      </div>
      <List
        listRef={listRef}
        className="log-viewer"
        rowComponent={LogLine}
        rowCount={logLines.length}
        rowHeight={rowHeight}
        rowProps={{ logLines, errorLineNumber }}
      />
    </>
  );
}

export default function App() {
  const [searchParams, setSearchParams] = useSearchParams();
  const selected = searchParams.get("selected");

  const [data, setData] = useState<Build[]>([]);
  const [commit, setCommit] = useState<Commit | null>(null);

  const [selectedBuild, setSelectedBuild] = useState<Build | null>(null);
  const [logContent, setLogContent] = useState<string>("");

  useEffect(() => {
    fetch(`/api/builds`)
      .then((res) => res.json())
      .then((res: ApiResponse) => {
        setData(res.builds);

        const counts: Record<string, number> = { "all": res.builds.length };

        for (const build of res.builds) {
          counts[build.tag] = (counts[build.tag] || 0) + 1;
        }

        setTags(counts);

        if (!selected) return;
        let idx = res.builds.findIndex((b) => b.attrpath == selected);

        if (idx == -1) return;
        selectBuild(res.builds[idx]);
        setCommit(res.commit);
      });
  }, []);

  const [query, setQuery] = useState("");
  const [mode, setMode] = useState<"name" | "content">("name");
  const [searchResults, setSearchResults] = useState<Build[] | null>(null);

  const [tags, setTags] = useState<Record<string, number>>({});
  const [activeTag, setActiveTag] = useState<string>(searchParams.get("tag") ?? "all");

  const filteredData = useMemo(() => {
    if (!query || mode !== "name") return data;

    const q = query.toLowerCase();

    return data.filter((b) =>
      b.attrpath.toLowerCase().includes(q)
    );
  }, [data, query, mode]);

  const selectBuild = (b: Build) => {
    setSelectedBuild(b);
    setSearchParams({ selected: b.attrpath });

    fetch(`/build-logs/${b.attrpath}.log`)
      .then((res) => res.text())
      .then((text) => setLogContent(text))
  }

  const prettifyDate = (iso: string | null) => {
    if (iso === null) return "";
    const date = new Date(iso);
    return date.toDateString();
  }

  useEffect(() => {
    if (mode !== "content") return;
    if (query.length < 3) {
      setSearchResults(data);
      return;
    }

    const controller = new AbortController();

    const id = setTimeout(() => {
      fetch(`/api/search?q=${encodeURIComponent(query)}`, {
        signal: controller.signal,
      })
        .then((res) => res.json())
        .then((res) => {
          const matched = new Set(res);
          setSearchResults(data.filter((b) => matched.has(b.attrpath)));
        })
        .catch((e) => {
          if (e.name !== "AbortError") console.error(e);
        });
    }, 300);

    return () => {
      controller.abort();
      clearTimeout(id);
    };
  }, [query, mode, data]);

  const displayed = useMemo(() => {
    let source = (mode === "content") ? (searchResults ?? []) : filteredData;

    if (activeTag == "all")
        return source;

    return source.filter((b: Build) => b.tag == activeTag);
  }, [mode, activeTag, filteredData, searchResults]);

  const copyAttrpaths = () => {
    navigator.clipboard.writeText(
      displayed.map(build => build.attrpath).join('\n')
    );
  };

  if (data.length === 0) {
    return (
      <div className="loading">
        <img className="spinning-nix" src="/nix.svg" height="24px" width="24px" alt=""/>
        <p>Loading (this might take a few seconds)...</p>
      </div>
    );
  }

  return (
    <div className="panel-hsplit">
      <div className="panel-dual-view">
        <div className="panel panel-tags">
          {Object.entries(tags)
            .sort((a, b) => b[1] - a[1])
            .map(([name, count]) => (
              <div
                key={name}
                className={`tag-item ${activeTag === name ? "active" : ""}`}
                onClick={() => setActiveTag(name)}
              >
                <span className="tag-item-name">{name}</span>
                <span className="tag-item-count">{count}</span>
              </div>
            ))}
        </div>

        <div className="panel-left">
          <div className="panel panel-left-top">
            <label>Search</label>
            <input
              placeholder={mode === "name" ? "e.g. curl" : "e.g. hash mismatch (3 characters minimum)"}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              maxLength={64}
            />
            <div className="mode-type">
              mode:
              <button
                className={"search-mode " + (mode === "name" ? " selected" : "")}
                onClick={() => setMode("name")}
              >name</button>
              <button
                className={"search-mode " + (mode === "content" ? " selected" : "")}
                onClick={() => setMode("content")}
              >grep</button>
            </div>
          </div>
      
          <div className="panel panel-left-bottom">
            <div className="panel-vsplit">
              <h2>Results ({displayed.length})</h2>
              <button className="btn" onClick={copyAttrpaths}>copy</button>
            </div>
            <BuildsTable
              builds={displayed}
              top={selected}
              selected={selectedBuild?.attrpath ?? null}
              onSelect={selectBuild}
            />
          </div>
        </div>

        <div className="panel panel-right">
          <div className="log-meta">
            <div className="log-meta-header">
              <h2>Log Viewer</h2>
              { selectedBuild && (
                selectedBuild.last_success_date
                  ? <p>Last succeeded: {prettifyDate(selectedBuild.last_success_date)} (<a href={`https://github.com/NixOS/nixpkgs/commit/${selectedBuild.last_success_rev}`}>{selectedBuild.last_success_rev!.slice(0, 7)}</a>)</p>
                  : <p>No successful build recorded</p>
              )}
            </div>
            {selectedBuild ? (
            <>
                <p>
                  Viewing { selectedBuild.attrpath }
                </p>
                { selectedBuild.hydra_id &&
                  <a href={`https://hydra.nixos.org/build/${ selectedBuild.hydra_id }`}>hydra</a>
                }
            </>
          ) : (
            <p>Select a build to view its log</p>
          )}
          </div>
          <span className="separator"></span>
          {selectedBuild &&
            <LogViewer
              logContent={logContent}
              errorLineNumber={selectedBuild.error_line_number}
            />
          }
        </div>
      </div>
    
      <div className="info panel-vsplit">
        <div className="info">
          <p>Last index: {prettifyDate(commit?.date ?? null)}</p>
          @
          <a href={`https://github.com/NixOS/nixpkgs/commit/${commit?.rev}`}>{commit?.name}</a>
          -
          <p>All the derivations are built by my tiny server, locally. x86_64-linux only.</p>
        </div>
        <div className="info">
          Contribution is welcome.
          <a href="https://github.com/Sigmanificient/nixpkgs-failure-dashboard">GitHub</a>
          /
          <a href="https://github.com/Sigmanificient/nixpkgs-failure-dashboard/issues/new">Report an issue</a>
        </div>
      </div>
    </div>
  );
}
