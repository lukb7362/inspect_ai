const loggingIcons: Record<string, string> = {
  notset: "bi bi-card-text",
  debug: "bi bi-bug",
  http: "bi bi-download",
  info: "bi bi-info-square",
  warning: "bi bi-exclamation-triangle",
  error: "bi bi-x-circle",
  critical: "bi bi-fire",
};

export const ApplicationIcons = {
  approve: "bi bi-shield",
  approvals: {
    approve: "bi bi-shield-check",
    reject: "bi bi-shield-x",
    terminate: "bi bi-shield-exclamation",
    escalate: "bi bi-box-arrow-up",
    modify: "bi bi-pencil-square",
  },
  arrows: {
    right: "bi bi-arrow-right",
    down: "bi bi-arrow-down",
    up: "bi bi-arrow-up",
  },
  caret: {
    right: "bi bi-caret-right",
    down: "bi bi-caret-down",
  },
  changes: {
    add: "bi bi-plus",
    remove: "bi bi-dash",
    replace: "bi bi-plus-slash-minus",
  },
  chevron: {
    right: "bi bi-chevron-right",
    down: "bi bi-chevron-down",
  },
  collapse: {
    all: "bi bi-arrows-collapse",
    up: "bi bi-chevron-up",
  },
  close: "bi bi-x",
  config: "bi bi-gear",
  confirm: "bi bi-check",
  copy: "bi bi-copy",
  epoch: (epoch: string) => {
    return `bi bi-${epoch}-circle`;
  },
  error: "bi bi-exclamation-circle",
  "expand-all": "bi bi-arrows-expand",
  "expand-down": "bi bi-chevron-down",
  fork: "bi bi-signpost-split",
  info: "bi bi-info-circle",
  input: "bi bi-terminal",
  inspect: "bi bi-gear",
  json: "bi bi-filetype-json",
  limits: {
    messages: "bi bi-chat-right-text",
    custom: "bi bi-person-workspace",
    operator: "bi bi-person-workspace",
    tokens: "bi bi-list",
    time: "bi bi-clock",
    execution: "bi bi-stopwatch",
  },
  logging: loggingIcons,
  menu: "bi bi-list",
  messages: "bi bi-chat-right-text",
  metadata: "bi bi-table",
  model: "bi bi-grid-3x3-gap",
  "toggle-right": "bi bi-chevron-right",
  more: "bi bi-zoom-in",
  "multiple-choice": "bi bi-card-list",
  next: "bi bi-chevron-right",
  noSamples: "bi bi-ban",
  play: "bi bi-play-fill",
  previous: "bi bi-chevron-left",
  refresh: "bi bi-arrow-clockwise",
  role: {
    user: "bi bi-person",
    system: "bi bi-cpu",
    assistant: "bi bi-robot",
    tool: "bi bi-tools",
    unknown: "bi bi-patch-question",
  },
  running: "bi bi-stars",
  sample: "bi bi-database",
  samples: "bi bi-file-spreadsheet",
  sandbox: "bi bi-box-seam",
  scorer: "bi bi-calculator",
  search: "bi bi-search",
  solvers: {
    default: "bi bi-arrow-return-right",
    generate: "bi bi-share",
    chain_of_thought: "bi bi-link",
    self_critique: "bi bi-arrow-left-right",
    system_message: "bi bi-cpu",
    use_tools: "bi bi-tools",
  },
  step: "bi bi-fast-forward-btn",
  subtask: "bi bi-subtract",
  transcript: "bi bi-list-columns-reverse",
  usage: "bi bi-stopwatch",
};
