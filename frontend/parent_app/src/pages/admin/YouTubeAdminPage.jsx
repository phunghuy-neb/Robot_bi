import YouTubeChannelManager from '../../components/YouTubeChannelManager.jsx';
import {
  adminGetYoutubeChannels,
  adminAddYoutubeChannel,
  adminRemoveYoutubeChannel,
} from '../../services/api.js';

// Admin: allowlist kênh YouTube GLOBAL — mọi gia đình đều thấy video từ các kênh này.
export default function YouTubeAdminPage() {
  return (
    <div>
      <p className="admin-page-note">
        Danh sách kênh chung cho <b>toàn bộ tài khoản</b>. Chỉ video từ các kênh ở đây mới hiển thị
        (không tìm kiếm mở YouTube) — đây là ranh giới an toàn cho trẻ. Mỗi phụ huynh có thể thêm
        kênh riêng cho gia đình mình trong app.
      </p>
      <YouTubeChannelManager
        loadFn={adminGetYoutubeChannels}
        addFn={adminAddYoutubeChannel}
        removeFn={adminRemoveYoutubeChannel}
        buttonTone="primary"
      />
    </div>
  );
}
