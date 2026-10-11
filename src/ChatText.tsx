import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";

export function ChatText({children}: {children: string}) {
  return <div className="chat-markdown"><Markdown remarkPlugins={[remarkGfm]} skipHtml
    disallowedElements={["img", "input"]}
    components={{a: ({children, href}) => <a href={href} target="_blank" rel="noreferrer noopener">{children}</a>,
      table: ({children}) => <div className="chat-table-scroll"><table>{children}</table></div>}}
  >{children}</Markdown></div>;
}
