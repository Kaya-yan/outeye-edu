import type { Metadata } from "next";
import LegalDocShell, { LegalSection } from "@/components/LegalDocShell";

export const metadata: Metadata = {
  title: "隐私政策 - OutEye Edu",
};

const COL_HEAD = "px-3 py-2 text-left text-xs font-semibold text-ink-500";
const COL_CELL = "px-3 py-2 align-top text-ink-700";

export default function PrivacyPage() {
  return (
    <LegalDocShell title="隐私政策" effectiveDate="2026年8月28日">
      <LegalSection title="一、运营者与联系方式">
        <p>本政策适用于 OutEye Edu（edu.outeye.top，以下简称「本平台」）提供的服务。</p>
        <p>我们以最小必要原则收集和使用您的个人信息。</p>
      </LegalSection>

      <LegalSection title="二、我们收集哪些信息">
        <table className="w-full border-collapse text-sm leading-[1.8]">
          <thead>
            <tr className="border-b border-black/10">
              <th className={COL_HEAD}>场景</th>
              <th className={COL_HEAD}>信息内容</th>
            </tr>
          </thead>
          <tbody>
            <tr className="border-b border-black/5">
              <td className={`${COL_CELL} whitespace-nowrap`}>注册</td>
              <td className={COL_CELL}>邮箱地址、姓名</td>
            </tr>
            <tr className="border-b border-black/5">
              <td className={`${COL_CELL} whitespace-nowrap`}>上传文件</td>
              <td className={COL_CELL}>课文文本与图片（每用户存储配额 100MB，超出后将无法继续上传）</td>
            </tr>
            <tr>
              <td className={`${COL_CELL} whitespace-nowrap`}>使用服务</td>
              <td className={COL_CELL}>生成的教案与课件、操作日志（用于服务运行与问题排查）</td>
            </tr>
          </tbody>
        </table>
        <p>我们不收集手机号、身份证号、生物识别信息等敏感个人信息。</p>
      </LegalSection>

      <LegalSection title="三、信息的使用">
        <p>我们收集的信息仅用于：</p>
        <ul className="list-disc space-y-1.5 pl-5">
          <li>提供课文分析与教案、课件生成功能；</li>
          <li>账号认证与服务运行保障；</li>
          <li>服务安全与问题排查；</li>
          <li>（仅限您主动共享的内容）供其他注册用户在公共资料区查看。</li>
        </ul>
        <p>我们不出售您的个人信息。</p>
      </LegalSection>

      <LegalSection title="四、第三方共享与披露">
        <table className="w-full border-collapse text-sm leading-[1.8]">
          <thead>
            <tr className="border-b border-black/10">
              <th className={COL_HEAD}>接收方</th>
              <th className={COL_HEAD}>目的</th>
              <th className={COL_HEAD}>传输的信息</th>
            </tr>
          </thead>
          <tbody>
            <tr className="border-b border-black/5">
              <td className={COL_CELL}>DeepSeek（深度求索）API</td>
              <td className={COL_CELL}>AI 生成教案、课件</td>
              <td className={COL_CELL}>课文文本与分析上下文</td>
            </tr>
            <tr className="border-b border-black/5">
              <td className={COL_CELL}>阿里云 OCR（通用文字识别）</td>
              <td className={COL_CELL}>图片文字识别</td>
              <td className={COL_CELL}>您上传的图片</td>
            </tr>
            <tr>
              <td className={COL_CELL}>阿里云（境内云服务）</td>
              <td className={COL_CELL}>服务器与数据托管</td>
              <td className={COL_CELL}>上述全部数据</td>
            </tr>
          </tbody>
        </table>
        <p>上述第三方按其各自的隐私政策处理接收到的信息，我们仅在实现对应功能所必需的范围内传输。</p>
        <p>除依法定要求配合司法机关或行政机关外，我们不会向其他任何第三方提供您的个人信息。</p>
      </LegalSection>

      <LegalSection title="五、存储地点与期限">
        <p>您的个人信息存储于中华人民共和国境内（阿里云青岛地域）。</p>
        <p>存储期限为账号存续期间；账号注销后，我们将删除您的个人信息或对其进行匿名化处理。</p>
      </LegalSection>

      <LegalSection title="六、您的权利">
        <p><strong>查阅与更正：</strong>您可以在「个人中心」查看和更正账号信息。</p>
        <p><strong>删除内容：</strong>您可以在各内容页面随时删除自己上传的内容和生成的教案、课件。</p>
        <p><strong>注销账号：</strong>发送邮件至 Kaya-yan@outlook.com 申请注销，我们核实您的身份后为您注销账号并删除数据。</p>
      </LegalSection>

      <LegalSection title="七、政策更新">
        <p>本政策更新时，我们会在本页面公示并更新生效日期。</p>
      </LegalSection>

      <LegalSection title="八、投诉与联系">
        <p>如您对本政策或个人信息处理事项有投诉、询问，请发送邮件至 Kaya-yan@outlook.com，我们承诺在 15 个工作日内予以响应。</p>
        <p>您对我们的答复不满意的，还可以依法向网信部门投诉、举报。</p>
      </LegalSection>

      <LegalSection title="九、生效日期">
        <p>本政策自 2026 年 8 月 28 日起生效。</p>
      </LegalSection>
    </LegalDocShell>
  );
}
