import { Modal, Form, Input, Upload, Button, message } from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import { useState } from 'react'

interface CreateProjectProps {
  visible: boolean
  onCancel: () => void
  onCreate: (values: any) => void
}

function CreateProject({ visible, onCancel, onCreate }: CreateProjectProps) {
  const [form] = Form.useForm()
  const [fileList, setFileList] = useState<any[]>([])

  const handleOk = async () => {
    try {
      const values = await form.validateFields()
      onCreate({
        ...values,
        files: fileList,
      })
      form.resetFields()
      setFileList([])
    } catch (error) {
      message.error('请填写完整信息')
    }
  }

  const uploadProps = {
    onRemove: (file: any) => {
      const index = fileList.indexOf(file)
      const newFileList = fileList.slice()
      newFileList.splice(index, 1)
      setFileList(newFileList)
    },
    beforeUpload: (file: any) => {
      setFileList([...fileList, file])
      return false
    },
    fileList,
  }

  return (
    <Modal
      title="新建项目"
      open={visible}
      onOk={handleOk}
      onCancel={() => {
        form.resetFields()
        setFileList([])
        onCancel()
      }}
    >
      <Form form={form} layout="vertical">
        <Form.Item
          name="name"
          label="项目名称"
          rules={[{ required: true, message: '请输入项目名称' }]}
        >
          <Input placeholder="请输入项目名称" />
        </Form.Item>
        <Form.Item name="description" label="项目描述">
          <Input.TextArea rows={4} placeholder="请输入项目描述" />
        </Form.Item>
        <Form.Item name="priority" label="优先级" initialValue="medium">
          <Input type="hidden" />
        </Form.Item>
        <Form.Item label="上传文件">
          <Upload {...uploadProps}>
            <Button icon={<PlusOutlined />}>选择文件</Button>
          </Upload>
        </Form.Item>
      </Form>
    </Modal>
  )
}

export default CreateProject
