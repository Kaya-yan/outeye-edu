import type { Metadata } from "next";
import LegalDocShell, { LegalSection } from "@/components/LegalDocShell";

export const metadata: Metadata = {
  title: "用户协议 - OutEye Edu",
};

export default function TermsPage() {
  return (
    <LegalDocShell title="用户协议" effectiveDate="2026年8月28日">
      <LegalSection title="一、协议的接受">
        <p>本协议是您与 OutEye Edu（edu.outeye.top，以下简称「本平台」）之间关于使用本平台服务所订立的条款。</p>
        <p>
          您在注册时勾选同意、点击「注册」或继续使用本平台服务的，均视为您已阅读并同意本协议全部条款。
          如果您不同意本协议，请停止注册或使用本平台服务。
        </p>
      </LegalSection>

      <LegalSection title="二、服务性质与用途">
        <p>本平台是面向大学外语教师（英语、法语、翻译等多语种）的 AI 备课助手，提供课文分析、教学方案生成、课件制作等辅助功能。</p>
        <p>本平台仅供教学与研究用途使用，不提供学历教育、商业培训或相关认证服务。当前为 1.0 版本，功能将持续迭代改进。</p>
      </LegalSection>

      <LegalSection title="三、账号注册与保管">
        <p>注册账号需提供真实有效的邮箱地址和姓名。您应确保注册信息真实，并对自己账号下的全部操作负责。</p>
        <p>账号和密码由您自行保管。因您保管不善或主动泄露导致的账号安全问题及相关损失，由您自行承担；发现账号被他人盗用时，请及时联系我们。</p>
        <p>本平台不会以任何方式向您索要密码，也不提供密码代管服务。</p>
      </LegalSection>

      <LegalSection title="四、用户上传内容">
        <p><strong>权属：</strong>您上传的课文、文件以及使用本平台生成的教案、课件等内容，相关权利归您本人所有。</p>
        <p>
          <strong>平台授权：</strong>
          为向您提供存储、文件解析、AI 生成、知识检索等服务所必需，您授权本平台在必要范围内处理上述内容。
        </p>
        <p>
          <strong>共享授权：</strong>
          您主动勾选共享到公共资料区的内容，视为您授权其他注册用户查看和使用。您可以随时取消共享或删除相关内容，删除后该内容不再出现在公共资料区。
        </p>
      </LegalSection>

      <LegalSection title="五、禁止行为">
        <p>您在使用本平台时，不得从事下列行为：</p>
        <ul className="list-disc space-y-1.5 pl-5">
          <li>上传违反法律法规、危害国家安全或社会公共利益的内容；</li>
          <li>上传侵犯他人著作权、肖像权等合法权益的内容（包括未经授权的他人作品）；</li>
          <li>对本平台进行恶意攻击、批量注册、非法抓取数据或其他危害服务正常运行的行为；</li>
          <li>超出正常教学研究用途，转售或变相转售本平台的生成内容与服务。</li>
        </ul>
        <p>出现上述行为时，本平台有权删除相关内容、限制或终止相关账号的服务。</p>
      </LegalSection>

      <LegalSection title="六、AI 生成内容声明">
        <p>本平台生成的教案、课件等内容由人工智能（AI）生成，仅供参考，可能存在不准确或不完善之处。</p>
        <p>您作为教师，应在专业判断的基础上对生成内容进行审阅和修改后再使用。本平台不对生成内容所涉教学内容的教学效果作任何保证，重要教学决策请以您本人的专业判断为准。</p>
      </LegalSection>

      <LegalSection title="七、未成年人条款">
        <p>本平台面向高校教师提供服务，不面向未成年人。未成年人请勿注册或使用本平台。</p>
      </LegalSection>

      <LegalSection title="八、服务变更与终止">
        <p>本平台可能因维护、升级等原因调整、暂停或终止部分服务，届时将尽量提前公告。</p>
        <p>您可随时停止使用本平台服务。您违反本协议时，本平台有权终止向您提供服务。</p>
      </LegalSection>

      <LegalSection title="九、其他">
        <p>本协议的订立、履行与争议解决适用中华人民共和国法律。</p>
        <p>本协议自 2026 年 8 月 28 日起生效。协议更新后将在本页面公示新的生效日期，您继续使用即视为接受更新后的协议。</p>
      </LegalSection>
    </LegalDocShell>
  );
}
